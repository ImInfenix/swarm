from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Project, Ticket


class TicketSuggestionTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="test-password-123")
        self.project = Project.objects.create(name="Demo", owner=self.author)
        self.other = Project.objects.create(name="Other", owner=self.author)

    def ticket(self, title, project=None, **kwargs):
        return Ticket.objects.create(project=project or self.project, author=self.author, type=Ticket.Type.FEATURE, title=title, description="Details", **kwargs)

    def test_suggestions_match_words_and_exclude_hidden_duplicates_and_other_projects(self):
        expected = self.ticket("Inventory crash when opening")
        self.ticket("Inventory crash hidden", is_hidden=True)
        self.ticket("Inventory crash elsewhere", project=self.other)
        self.ticket("Inventory crash duplicate", duplicate_of=expected)
        url = reverse("api_ticket_suggestions", args=[self.project.slug])
        response = self.client.get(url, {"q": "crash inventory"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [expected.pk])
        self.assertEqual(response.json()[0]["url"], expected.get_absolute_url())
        self.assertEqual(self.client.get(url, {"q": "in"}).json(), [])
        self.assertEqual(self.client.get(url, {"q": "missing"}).json(), [])

    def test_create_form_contains_suggestions_endpoint(self):
        self.client.force_login(self.author)
        response = self.client.get(reverse("ticket_create", args=[self.project.slug]))
        self.assertContains(response, reverse("api_ticket_suggestions", args=[self.project.slug]))
        self.assertContains(response, "Possible existing tickets")
