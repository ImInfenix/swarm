from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .api_auth import issue_api_token
from .models import Project, ProjectVersion, Ticket


class CommunityTicketTests(TestCase):
    def setUp(self):
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
