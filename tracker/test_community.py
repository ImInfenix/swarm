from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .api_auth import issue_api_token
from .models import Comment, ContentReport, Project, ProjectVersion, Ticket, TicketVote
from .rate_limits import allow_action, client_address


class CommunityTicketTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(username="owner", password="strong-password-123")
        self.member = User.objects.create_user(username="member", password="strong-password-123")
        self.project = Project.objects.create(name="Game", slug="game", owner=self.owner)
        self.other_project = Project.objects.create(name="Other", slug="other", owner=self.owner)

    def bug_data(self, version_id):
        return {
            "type": "bug",
            "title": "Inventory closes unexpectedly",
            "description": "The inventory closes during combat.",
            "steps_to_reproduce": "Open inventory and take damage.",
            "expected_result": "Inventory remains open.",
            "actual_result": "Inventory closes.",
            "affected_version": version_id,
        }

    def test_web_ticket_types_versions_and_owner_release(self):
        self.client.force_login(self.member)
        version_url = reverse("project_version_create", args=["game"])
        self.assertEqual(self.client.post(version_url, {"name": "1.0"}).status_code, 403)
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(version_url, {"name": "1.0"}), reverse("project_detail", args=["game"]))
        version = ProjectVersion.objects.get(project=self.project)
        self.assertContains(self.client.get(reverse("project_detail", args=["game"])), "1.0")
        self.assertEqual(self.client.post(version_url, {"name": "1.0"}).status_code, 200)
        self.assertEqual(ProjectVersion.objects.filter(project=self.project).count(), 1)
        self.assertEqual(self.client.post(version_url, {"name": "2.0", "released_on": "2099-01-01"}).status_code, 200)
        self.assertEqual(ProjectVersion.objects.filter(project=self.project).count(), 1)
        self.client.force_login(self.member)
        ticket_url = reverse("ticket_create", args=["game"])
        data = self.bug_data(version.pk)
        data["steps_to_reproduce"] = ""
        self.assertContains(self.client.post(ticket_url, data), "This field is required for bug reports.")
        self.assertFalse(Ticket.objects.exists())
        data["steps_to_reproduce"] = "Open inventory and take damage."
        foreign_version = ProjectVersion.objects.create(project=self.other_project, name="1.0")
        data["affected_version"] = foreign_version.pk
        self.assertEqual(self.client.post(ticket_url, data).status_code, 200)
        self.assertFalse(Ticket.objects.exists())
        data["affected_version"] = version.pk
        self.assertEqual(self.client.post(ticket_url, data).status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.type, Ticket.Type.BUG)
        self.assertEqual(ticket.affected_version, version)
        self.assertTrue(TicketVote.objects.filter(ticket=ticket, user=self.member).exists())
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "▲ 1")
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "Remove vote")
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "Steps to reproduce")
        self.client.force_login(self.owner)
        triage_url = reverse("ticket_triage", args=[ticket.pk])
        triage = {"status": "resolved", "priority": "normal", "target_version": version.pk, "fixed_version": version.pk}
        self.assertEqual(self.client.post(triage_url, triage).status_code, 200)
        self.assertIsNone(Ticket.objects.get(pk=ticket.pk).fixed_version)
        edit_url = reverse("project_version_edit", args=["game", version.pk])
        self.assertRedirects(self.client.post(edit_url, {"name": "1.0", "released_on": "2026-10-13"}), reverse("project_detail", args=["game"]))
        self.assertRedirects(self.client.post(triage_url, triage), reverse("ticket_detail", args=[ticket.pk]))
        ticket.refresh_from_db()
        self.assertEqual(ticket.target_version, version)
        self.assertEqual(ticket.fixed_version, version)
        self.assertEqual(self.client.post(edit_url, {"name": "1.0", "released_on": ""}).status_code, 200)
        self.client.post(reverse("set_language"), {"language": "fr"})
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "Version concernée")

    def test_api_versions_and_bug_validation(self):
        owner_token, _ = issue_api_token(self.owner)
        member_token, _ = issue_api_token(self.member)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {member_token}")
        versions_url = reverse("api_project_versions", args=["game"])
        self.assertEqual(client.post(versions_url, {"name": "1.0"}, format="json").status_code, 403)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token}")
        created = client.post(versions_url, {"name": "1.0"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        version_id = created.data["id"]
        self.assertEqual(client.post(versions_url, {"name": "1.0"}, format="json").status_code, 400)
        self.assertEqual(client.post(versions_url, {"name": "2.0", "released_on": "2099-01-01"}, format="json").status_code, 400)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {member_token}")
        self.assertEqual(client.get(versions_url).data[0]["id"], version_id)
        ticket_url = reverse("api_project_tickets", args=["game"])
        data = self.bug_data(version_id)
        data["actual_result"] = ""
        self.assertEqual(client.post(ticket_url, data, format="json").status_code, 400)
        data["actual_result"] = "Inventory closes."
        foreign = ProjectVersion.objects.create(project=self.other_project, name="2.0")
        data["affected_version"] = foreign.pk
        self.assertEqual(client.post(ticket_url, data, format="json").status_code, 400)
        data["affected_version"] = version_id
        created_ticket = client.post(ticket_url, data, format="json")
        self.assertEqual(created_ticket.status_code, 201, created_ticket.data)
        self.assertEqual(created_ticket.data["affected_version"], version_id)
        ticket_id = created_ticket.data["id"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token}")
        triage_url = reverse("api_ticket_triage", args=[ticket_id])
        self.assertEqual(client.patch(triage_url, {"target_version": foreign.pk}, format="json").status_code, 400)
        self.assertEqual(client.patch(triage_url, {"fixed_version": version_id}, format="json").status_code, 400)
        version_url = reverse("api_project_version_detail", args=["game", version_id])
        self.assertEqual(client.patch(version_url, {"released_on": "2026-10-13"}, format="json").status_code, 200)
        triaged = client.patch(triage_url, {"target_version": version_id, "fixed_version": version_id}, format="json")
        self.assertEqual(triaged.status_code, 200, triaged.data)
        self.assertEqual(triaged.data["fixed_version"], version_id)
        self.assertEqual(client.patch(version_url, {"released_on": None}, format="json").status_code, 400)

    def test_web_vote_and_popular_ticket_order(self):
        first = Ticket.objects.create(project=self.project, author=self.owner, type=Ticket.Type.FEATURE, title="First feature", description="Details")
        second = Ticket.objects.create(project=self.project, author=self.owner, type=Ticket.Type.FEATURE, title="Second feature", description="Details")
        vote_url = reverse("ticket_vote", args=[first.pk])
        self.assertEqual(self.client.post(vote_url, {"action": "add"}).status_code, 302)
        self.client.force_login(self.member)
        self.assertRedirects(self.client.post(vote_url, {"action": "add"}), reverse("ticket_detail", args=[first.pk]))
        self.assertRedirects(self.client.post(vote_url, {"action": "add"}), reverse("ticket_detail", args=[first.pk]))
        self.assertEqual(TicketVote.objects.filter(ticket=first).count(), 2)
        self.assertContains(self.client.get(reverse("ticket_detail", args=[first.pk])), "Remove vote")
        self.client.post(reverse("set_language"), {"language": "fr"})
        self.assertContains(self.client.get(reverse("ticket_detail", args=[first.pk])), "Retirer mon vote")
        self.assertEqual(self.client.post(vote_url, {"action": "invalid"}).status_code, 400)
        popular = self.client.get(reverse("project_detail", args=["game"]), {"sort": "popular"})
        self.assertContains(popular, "Les plus soutenus")
        self.assertEqual(list(popular.context["page"].object_list), [first, second])
        self.assertRedirects(self.client.post(vote_url, {"action": "remove"}), reverse("ticket_detail", args=[first.pk]))
        self.assertEqual(TicketVote.objects.count(), 2)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.member)
        self.assertEqual(csrf_client.post(vote_url, {"action": "add"}).status_code, 403)

    def test_api_votes_and_filters(self):
        version = ProjectVersion.objects.create(project=self.project, name="1.0")
        first = Ticket.objects.create(project=self.project, author=self.owner, type=Ticket.Type.BUG, title="Old bug", description="Details", affected_version=version)
        second = Ticket.objects.create(project=self.project, author=self.owner, type=Ticket.Type.FEATURE, title="New feature", description="Details")
        vote_url = reverse("api_ticket_vote", args=[first.pk])
        client = APIClient()
        self.assertEqual(client.put(vote_url, {}, format="json").status_code, 401)
        token, _ = issue_api_token(self.member)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.put(vote_url, {}, format="json").data["vote_count"], 2)
        self.assertEqual(client.put(vote_url, {}, format="json").data["vote_count"], 2)
        listing = client.get(reverse("api_project_tickets", args=["game"]), {"sort": "popular"})
        self.assertEqual([ticket["id"] for ticket in listing.data["results"]], [first.pk, second.pk])
        self.assertEqual(listing.data["results"][0]["vote_count"], 2)
        self.assertEqual(client.get(reverse("api_ticket_list"), {"type": "bug", "version": version.pk}).data["count"], 1)
        self.assertEqual(client.get(reverse("api_ticket_list"), {"type": "feature", "version": version.pk}).data["count"], 0)
        self.assertEqual(client.delete(vote_url).data["vote_count"], 1)
        self.assertEqual(client.delete(vote_url).data["vote_count"], 1)

    def test_triage_dashboard_and_duplicate_redirect(self):
        original = Ticket.objects.create(project=self.project, author=self.member, type=Ticket.Type.FEATURE, title="Main request", description="Details")
        duplicate = Ticket.objects.create(project=self.project, author=self.member, type=Ticket.Type.FEATURE, title="Repeated request", description="Details")
        foreign = Ticket.objects.create(project=self.other_project, author=self.member, type=Ticket.Type.FEATURE, title="Other project", description="Details")
        TicketVote.objects.create(ticket=duplicate, user=self.owner)
        dashboard_url = reverse("project_triage_dashboard", args=["game"])
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(dashboard_url).status_code, 403)
        self.client.force_login(self.owner)
        dashboard = self.client.get(dashboard_url)
        self.assertContains(dashboard, "Main request")
        triage_url = reverse("ticket_triage", args=[duplicate.pk])
        data = {"status": "open", "priority": "normal", "duplicate_of": foreign.pk}
        self.assertEqual(self.client.post(triage_url, data).status_code, 200)
        data["duplicate_of"] = original.pk
        self.assertRedirects(self.client.post(triage_url, data), reverse("ticket_detail", args=[duplicate.pk]))
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.status, Ticket.Status.CLOSED)
        self.assertEqual(duplicate.duplicate_of, original)
        self.assertContains(self.client.get(reverse("ticket_detail", args=[duplicate.pk])), "Vote on the original ticket")
        self.assertContains(self.client.get(reverse("ticket_detail", args=[original.pk])), "▲ 2")
        self.assertEqual(self.client.post(reverse("ticket_vote", args=[duplicate.pk]), {"action": "add"}).status_code, 400)
        owner_token, _ = issue_api_token(self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token}")
        api_dashboard = client.get(reverse("api_project_triage_dashboard", args=["game"]))
        self.assertEqual(api_dashboard.status_code, 200)
        self.assertIn("unanswered", api_dashboard.data)
        self.assertEqual(client.put(reverse("api_ticket_vote", args=[duplicate.pk]), {}, format="json").status_code, 400)
        self.assertEqual(client.delete(reverse("api_ticket_vote", args=[duplicate.pk])).data["vote_count"], 1)
        self.assertEqual(client.get(reverse("api_ticket_detail", args=[original.pk])).data["vote_count"], 1)
        self.assertEqual(client.patch(reverse("api_ticket_triage", args=[original.pk]), {"duplicate_of": duplicate.pk}, format="json").status_code, 400)

    def test_content_reports_and_hidden_content(self):
        ticket = Ticket.objects.create(project=self.project, author=self.owner, type=Ticket.Type.FEATURE, title="Spam candidate", description="Details")
        comment = Comment.objects.create(ticket=ticket, author=self.owner, body="A comment")
        ticket_report_url = reverse("ticket_report", args=[ticket.pk])
        self.assertEqual(self.client.get(ticket_report_url).status_code, 302)
        self.client.force_login(self.member)
        self.assertContains(self.client.get(ticket_report_url), "Send report")
        self.assertRedirects(self.client.post(ticket_report_url, {"reason": "spam", "details": "Repeated post"}), reverse("ticket_detail", args=[ticket.pk]))
        self.assertRedirects(self.client.post(ticket_report_url, {"reason": "abuse"}), reverse("ticket_detail", args=[ticket.pk]))
        self.assertEqual(ContentReport.objects.filter(ticket=ticket).count(), 1)
        comment_report_url = reverse("comment_report", args=[comment.pk])
        self.assertRedirects(self.client.post(comment_report_url, {"reason": "abuse"}), reverse("ticket_detail", args=[ticket.pk]))
        self.assertEqual(ContentReport.objects.filter(comment=comment).count(), 1)
        token, _ = issue_api_token(self.member)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.post(reverse("api_ticket_report", args=[ticket.pk]), {"reason": "spam"}, format="json").status_code, 200)
        self.assertEqual(client.post(reverse("api_comment_report", args=[comment.pk]), {"reason": "abuse"}, format="json").status_code, 200)
        self.assertEqual(client.post(reverse("api_ticket_report", args=[ticket.pk]), {"reason": "invalid"}, format="json").status_code, 400)
        comment.is_hidden = True
        comment.save(update_fields=["is_hidden"])
        self.assertNotContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "A comment")
        self.assertEqual(client.get(reverse("api_ticket_comments", args=[ticket.pk])).data["count"], 0)
        ticket.is_hidden = True
        ticket.save(update_fields=["is_hidden"])
        self.assertEqual(self.client.get(reverse("ticket_detail", args=[ticket.pk])).status_code, 404)
        self.assertEqual(client.get(reverse("api_ticket_detail", args=[ticket.pk])).status_code, 404)
        self.assertEqual(client.put(reverse("api_ticket_vote", args=[ticket.pk]), {}, format="json").status_code, 404)
        self.assertRedirects(self.client.post(reverse("delete_account"), {"confirm": "delete"}), reverse("home"))
        self.assertEqual(ContentReport.objects.filter(reporter__isnull=True).count(), 2)

    def test_rate_limit_and_trusted_proxy_address(self):
        self.assertTrue(allow_action("sample", "member", 2, 3600))
        self.assertTrue(allow_action("sample", "member", 2, 3600))
        self.assertFalse(allow_action("sample", "member", 2, 3600))
        request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="spoofed, 198.51.100.2")
        self.assertEqual(client_address(request), "127.0.0.1")
        with override_settings(SWARM_TRUSTED_PROXY_IPS=["127.0.0.1"]):
            self.assertEqual(client_address(request), "198.51.100.2")
        ticket = Ticket.objects.create(project=self.project, author=self.owner, type=Ticket.Type.FEATURE, title="Idea", description="Details")
        self.client.force_login(self.member)
        for _ in range(120):
            allow_action("vote", self.member.pk, 120, 3600)
        self.assertEqual(self.client.post(reverse("ticket_vote", args=[ticket.pk]), {"action": "add"}).status_code, 429)
        self.assertFalse(TicketVote.objects.filter(ticket=ticket, user=self.member).exists())

    def test_admin_can_hide_content_and_resolve_reports(self):
        ticket = Ticket.objects.create(project=self.project, author=self.member, type=Ticket.Type.FEATURE, title="Reported ticket", description="Details")
        comment = Comment.objects.create(ticket=ticket, author=self.member, body="Reported comment")
        report = ContentReport.objects.create(reporter=self.owner, ticket=ticket, reason=ContentReport.Reason.SPAM)
        staff = User.objects.create_superuser(username="staff", email="staff@example.com", password="strong-password-123")
        self.client.force_login(staff)
        actions = (
            ("admin:tracker_ticket_changelist", "hide_tickets", ticket.pk),
            ("admin:tracker_comment_changelist", "hide_comments", comment.pk),
            ("admin:tracker_contentreport_changelist", "resolve_reports", report.pk),
        )
        for route, action, pk in actions:
            response = self.client.post(reverse(route), {"action": action, "_selected_action": [pk]})
            self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        comment.refresh_from_db()
        report.refresh_from_db()
        self.assertTrue(ticket.is_hidden)
        self.assertTrue(comment.is_hidden)
        self.assertIsNotNone(report.resolved_at)
