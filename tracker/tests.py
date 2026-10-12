from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Comment, Project, Ticket


class TrackerFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="strong-test-password")
        self.member = User.objects.create_user(username="member", password="strong-test-password")
        self.project = Project.objects.create(name="Demo", slug="demo", description="Example", owner=self.owner)
        self.ticket = Ticket.objects.create(project=self.project, title="First issue", description="Details", author=self.member)

    def test_public_pages_and_filters(self):
        for name, args in (("home", []), ("project_list", []), ("project_detail", ["demo"]), ("ticket_list", []), ("ticket_detail", [self.ticket.pk])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)
        response = self.client.get(reverse("project_detail", args=["demo"]), {"status": "resolved"})
        self.assertNotContains(response, "First issue")
        response = self.client.get(reverse("project_detail", args=["demo"]), {"status": "open"})
        self.assertContains(response, "First issue")

    def test_guest_cannot_create_content(self):
        response = self.client.post(reverse("project_create"), {"name": "Other", "slug": "other"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(slug="other").exists())
        response = self.client.post(reverse("comment_create", args=[self.ticket.pk]), {"body": "Reply"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_member_can_create_project_ticket_and_comment(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("project_create"), {"name": "Second", "slug": "second", "description": "Another project"})
        self.assertRedirects(response, reverse("project_detail", args=["second"]))
        self.assertEqual(Project.objects.get(slug="second").owner, self.member)
        response = self.client.post(reverse("ticket_create", args=["demo"]), {"title": "New issue", "description": "A description"})
        created = Ticket.objects.get(title="New issue")
        self.assertRedirects(response, reverse("ticket_detail", args=[created.pk]))
        self.assertEqual(created.author, self.member)
        previous_activity = self.ticket.updated_at
        response = self.client.post(reverse("comment_create", args=[self.ticket.pk]), {"body": "A reply"})
        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(Comment.objects.get(body="A reply").author, self.member)
        self.ticket.refresh_from_db()
        self.assertGreaterEqual(self.ticket.updated_at, previous_activity)

    def test_only_owner_can_triage_and_edit_project(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(reverse("ticket_triage", args=[self.ticket.pk]), {"status": "resolved", "priority": "urgent"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("project_edit", args=["demo"]), {"name": "Changed", "description": "Changed"}).status_code, 403)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)
        self.client.force_login(self.owner)
        response = self.client.post(reverse("ticket_triage", args=[self.ticket.pk]), {"status": "resolved", "priority": "urgent"})
        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        self.assertEqual(self.ticket.priority, Ticket.Priority.URGENT)

    def test_only_author_can_edit_ticket(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("ticket_edit", args=[self.ticket.pk]), {"title": "Changed", "description": "Changed"})
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.member)
        response = self.client.post(reverse("ticket_edit", args=[self.ticket.pk]), {"title": "Changed", "description": "Changed"})
        self.assertRedirects(response, reverse("ticket_detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, "Changed")

    def test_signup_creates_account_and_session(self):
        response = self.client.post(reverse("signup"), {"username": "new-member", "email": "New@Example.com", "password1": "long-and-unique-password-123", "password2": "long-and-unique-password-123"})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(User.objects.get(username="new-member").email, "new@example.com")
        self.assertIn("_auth_user_id", self.client.session)

    def test_untrusted_next_does_not_redirect_externally(self):
        response = self.client.post(reverse("login"), {"username": "member", "password": "strong-test-password", "next": "https://example.com/"})
        self.assertRedirects(response, reverse("home"))
