from datetime import timedelta

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ApiToken, TicketVote


class ApiFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def signup(self, username):
        response = self.client.post(reverse("api_signup"), {
            "username": username,
            "email": f"{username}@example.com",
            "password1": "long-and-unique-password-123",
            "password2": "long-and-unique-password-123",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["token"]

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_public_read_and_authentication_required_for_writes(self):
        documentation = self.client.get(reverse("api_root"))
        self.assertEqual(documentation.status_code, 200)
        self.assertEqual(documentation.data["authentication"]["header"], "Authorization: Bearer <token>")
        self.assertTrue(any(endpoint["path"] == "/api/v1/projects/" for endpoint in documentation.data["endpoints"]))
        self.assertEqual(self.client.get(reverse("api_project_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("api_ticket_list")).status_code, 200)
        response = self.client.post(reverse("api_project_list"), {"name": "Demo"}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get(reverse("api_me")).status_code, 401)

    def test_signup_login_create_comment_and_revoke(self):
        token = self.signup("alice")
        self.assertNotEqual(ApiToken.objects.get().digest, token)
        self.authenticate(token)
        self.assertEqual(self.client.get(reverse("api_me")).data["username"], "alice")
        project = self.client.post(reverse("api_project_list"), {"name": "Équipe Projet Long", "description": "A project"}, format="json")
        self.assertEqual(project.status_code, 201, project.data)
        self.assertEqual(project.data["slug"], "equipe-pro")
        ticket = self.client.post(reverse("api_project_tickets", args=["equipe-pro"]), {"type": "feature", "title": "First issue", "description": "Details"}, format="json")
        self.assertEqual(ticket.status_code, 201, ticket.data)
        self.assertEqual(ticket.data["vote_count"], 1)
        self.assertTrue(TicketVote.objects.filter(ticket_id=ticket.data["id"], user__username="alice").exists())
        ticket_id = ticket.data["id"]
        comment = self.client.post(reverse("api_ticket_comments", args=[ticket_id]), {"body": "A reply"}, format="json")
        self.assertEqual(comment.status_code, 201, comment.data)
        self.assertEqual(comment.data["author"], "alice")
        self.assertEqual(self.client.get(reverse("api_ticket_comments", args=[ticket_id])).data["count"], 1)
        self.assertEqual(self.client.get(reverse("api_ticket_list"), {"project": "equipe-pro"}).data["count"], 1)
        self.assertEqual(self.client.delete(reverse("api_token")).status_code, 204)
        self.assertEqual(self.client.get(reverse("api_me")).status_code, 401)
        self.client.credentials()
        login = self.client.post(reverse("api_token"), {"username": "alice", "password": "long-and-unique-password-123"}, format="json")
        self.assertEqual(login.status_code, 200, login.data)
        self.assertNotEqual(login.data["token"], token)

    def test_api_permissions_and_triage(self):
        owner_token = self.signup("owner")
        self.authenticate(owner_token)
        project = self.client.post(reverse("api_project_list"), {"name": "Demo"}, format="json")
        self.assertEqual(project.status_code, 201, project.data)
        reporter_token = self.signup("reporter")
        self.authenticate(reporter_token)
        ticket = self.client.post(reverse("api_project_tickets", args=["demo"]), {"type": "feature", "title": "Issue", "description": "Details"}, format="json")
        self.assertEqual(ticket.status_code, 201, ticket.data)
        ticket_url = reverse("api_ticket_detail", args=[ticket.data["id"]])
        triage_url = reverse("api_ticket_triage", args=[ticket.data["id"]])
        self.assertEqual(self.client.patch(triage_url, {"status": "resolved"}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(reverse("api_project_detail", args=["demo"]), {"name": "Other"}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(ticket_url, {"status": "closed"}, format="json").status_code, 400)
        edited = self.client.patch(ticket_url, {"description": "More details"}, format="json")
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data["status"], "open")
        self.authenticate(owner_token)
        self.assertEqual(self.client.patch(ticket_url, {"title": "Changed"}, format="json").status_code, 403)
        updated_project = self.client.patch(reverse("api_project_detail", args=["demo"]), {"description": "Updated"}, format="json")
        self.assertEqual(updated_project.status_code, 200, updated_project.data)
        self.assertEqual(updated_project.data["description"], "Updated")
        triaged = self.client.patch(triage_url, {"status": "resolved", "priority": "urgent"}, format="json")
        self.assertEqual(triaged.status_code, 200, triaged.data)
        self.assertEqual(triaged.data["priority"], "urgent")
        self.assertEqual(self.client.get(reverse("api_project_tickets", args=["demo"]), {"status": "open"}).data["count"], 0)

    def test_invalid_input_and_credentials(self):
        token = self.signup("member")
        self.authenticate(token)
        response = self.client.post(reverse("api_project_list"), {"name": "<script>"}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse("api_project_list"), {"name": "Demo"}, format="json")
        self.assertEqual(response.status_code, 201)
        ticket_url = reverse("api_project_tickets", args=["demo"])
        for data in (
            {"title": "Missing type", "description": "Details"},
            {"type": "unclassified", "title": "Legacy type", "description": "Details"},
        ):
            response = self.client.post(ticket_url, data, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("type", response.data)
        response = self.client.post(ticket_url, {"type": "feature", "description": "Missing title"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.client.credentials()
        response = self.client.post(reverse("api_token"), {"username": "member", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse("api_token"), [], format="json")
        self.assertEqual(response.status_code, 400)

    def test_expired_token_is_rejected(self):
        token = self.signup("expired")
        ApiToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.authenticate(token)
        self.assertEqual(self.client.get(reverse("api_me")).status_code, 401)
