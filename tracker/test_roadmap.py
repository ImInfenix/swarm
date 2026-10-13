from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectVersion, Ticket


class RoadmapTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="test-password-123")
        self.project = Project.objects.create(name="Demo", owner=self.author)
        self.planned = ProjectVersion.objects.create(project=self.project, name="2.0")
        self.released = ProjectVersion.objects.create(project=self.project, name="1.0", released_on=date(2025, 1, 1))

    def ticket(self, title, **kwargs):
        return Ticket.objects.create(project=self.project, author=self.author, type=Ticket.Type.FEATURE, title=title, description="Details", **kwargs)

    def test_public_roadmap_separates_targets_deliveries_and_backlog(self):
        target = self.ticket("Planned improvement", target_version=self.planned)
        delivered = self.ticket("Delivered improvement", target_version=self.released, fixed_version=self.released, status=Ticket.Status.RESOLVED)
        missed = self.ticket("Needs replanning", target_version=self.released)
        self.ticket("Unscheduled improvement")
        self.ticket("Hidden plan", target_version=self.planned, is_hidden=True)
        self.ticket("Declined plan", target_version=self.planned, status=Ticket.Status.CLOSED)
        self.ticket("Duplicate plan", target_version=self.planned, duplicate_of=target)
        response = self.client.get(reverse("project_roadmap", args=[self.project.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Planned improvement")
        self.assertContains(response, "Delivered improvement")
        self.assertContains(response, "Needs replanning")
        self.assertNotContains(response, "Hidden plan")
        self.assertNotContains(response, "Declined plan")
        self.assertNotContains(response, "Duplicate plan")
        self.assertContains(response, f'id="version-{self.planned.pk}"')
        api_response = self.client.get(reverse("api_project_roadmap", args=[self.project.slug]))
        self.assertEqual(api_response.status_code, 200)
        data = api_response.json()
        self.assertEqual([ticket["id"] for ticket in data["planned_versions"][0]["tickets"]], [target.pk])
        self.assertEqual([ticket["id"] for ticket in data["released_versions"][0]["tickets"]], [delivered.pk])
        self.assertIn(missed.pk, [ticket["id"] for ticket in data["backlog"]])
        self.assertContains(self.client.get(target.get_absolute_url()), reverse("project_roadmap", args=[self.project.slug]))
