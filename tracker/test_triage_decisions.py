from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .api_auth import issue_api_token
from .models import Notification, Project, ProjectVersion, Ticket


class TriageDecisionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="test-password-123")
        self.author = User.objects.create_user(username="author", password="test-password-123")
        self.project = Project.objects.create(name="Demo", owner=self.owner)
        self.version = ProjectVersion.objects.create(project=self.project, name="2.0")
        self.ticket = Ticket.objects.create(project=self.project, author=self.author, type=Ticket.Type.FEATURE, title="Idea", description="Details")

    def test_web_closure_and_information_request_require_explanations(self):
        self.client.force_login(self.owner)
        url = reverse("ticket_triage", args=[self.ticket.pk])
        self.assertContains(self.client.post(url, {"status": "closed", "priority": "normal"}), "Choose a closure reason")
        self.assertContains(self.client.post(url, {"status": "closed", "priority": "normal", "closure_reason": "declined"}), "Explain this decision")
        response = self.client.post(url, {"status": "closed", "priority": "normal", "target_version": self.version.pk, "closure_reason": "declined", "decision_note": "Outside project scope."})
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.closure_reason, Ticket.ClosureReason.DECLINED)
        self.assertIsNone(self.ticket.target_version)
        self.assertContains(self.client.get(self.ticket.get_absolute_url()), "Outside project scope.")
        self.assertEqual(Notification.objects.filter(user=self.author).count(), 1)
        self.assertContains(self.client.post(url, {"status": "needs_info", "priority": "normal"}), "Explain what information is needed")
        self.assertEqual(self.client.post(url, {"status": "needs_info", "priority": "normal", "decision_note": "Which browser?"}).status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.closure_reason, "")
        self.assertEqual(self.ticket.decision_note, "Which browser?")
        self.assertContains(self.client.get(self.ticket.get_absolute_url()), "Which browser?")
        self.client.force_login(self.author)
        self.assertEqual(self.client.post(reverse("comment_create", args=[self.ticket.pk]), {"body": "Firefox 120."}).status_code, 302)
        self.assertTrue(Notification.objects.filter(user=self.owner, kind=Notification.Kind.COMMENT).exists())
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(url, {"status": "open", "priority": "normal"}).status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.decision_note, "")

    def test_api_requires_reason_and_sets_duplicate_reason(self):
        token, _ = issue_api_token(self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        url = reverse("api_ticket_triage", args=[self.ticket.pk])
        self.assertEqual(client.patch(url, {"status": "closed"}, format="json").status_code, 400)
        self.assertEqual(client.patch(url, {"status": "closed", "closure_reason": "cannot_reproduce", "decision_note": "Cannot repeat on 2.0."}, format="json").status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.closure_reason, Ticket.ClosureReason.CANNOT_REPRODUCE)
        other = Ticket.objects.create(project=self.project, author=self.author, type=Ticket.Type.FEATURE, title="Another idea", description="Details")
        duplicate_url = reverse("api_ticket_triage", args=[other.pk])
        response = client.patch(duplicate_url, {"duplicate_of": self.ticket.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["closure_reason"], Ticket.ClosureReason.DUPLICATE)
