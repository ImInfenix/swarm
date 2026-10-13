from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .api_auth import issue_api_token
from .models import Notification, Project, Ticket, TicketSubscription


class NotificationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="test-password-123")
        self.author = User.objects.create_user(username="author", password="test-password-123")
        self.follower = User.objects.create_user(username="follower", password="test-password-123")
        self.project = Project.objects.create(name="Demo", owner=self.owner)
        self.ticket = Ticket.objects.create(project=self.project, author=self.author, type=Ticket.Type.FEATURE, title="Search", description="Details")

    def test_author_follows_new_ticket_and_comment_notifies_other_followers(self):
        self.assertTrue(TicketSubscription.objects.filter(ticket=self.ticket, user=self.author).exists())
        self.client.force_login(self.follower)
        self.client.post(reverse("ticket_subscription", args=[self.ticket.pk]), {"action": "follow"})
        self.client.force_login(self.owner)
        self.client.post(reverse("comment_create", args=[self.ticket.pk]), {"body": "Update"})
        self.assertEqual(set(Notification.objects.values_list("user_id", flat=True)), {self.author.pk, self.follower.pk})
        self.client.force_login(self.author)
        response = self.client.get(reverse("notifications"))
        self.assertContains(response, "Search")
        self.assertContains(response, "Notifications")
        item = Notification.objects.get(user=self.author)
        self.assertEqual(self.client.post(reverse("notification_read", args=[item.pk])).status_code, 302)
        item.refresh_from_db()
        self.assertIsNotNone(item.read_at)
        self.client.force_login(self.follower)
        self.assertEqual(self.client.post(reverse("notification_read", args=[item.pk])).status_code, 404)

    def test_web_and_api_triage_notify_only_on_change(self):
        self.client.force_login(self.owner)
        url = reverse("ticket_triage", args=[self.ticket.pk])
        data = {"status": "in_progress", "priority": "normal", "target_version": "", "fixed_version": "", "duplicate_of": ""}
        self.client.post(url, data)
        self.assertEqual(Notification.objects.filter(user=self.author, kind=Notification.Kind.TRIAGE).count(), 1)
        self.client.post(url, data)
        self.assertEqual(Notification.objects.filter(user=self.author, kind=Notification.Kind.TRIAGE).count(), 1)
        token, _ = issue_api_token(self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.patch(reverse("api_ticket_triage", args=[self.ticket.pk]), {"priority": "high"}, format="json").status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.author, kind=Notification.Kind.TRIAGE).count(), 2)

    def test_unfollow_and_hidden_ticket(self):
        self.client.force_login(self.author)
        self.client.post(reverse("ticket_subscription", args=[self.ticket.pk]), {"action": "unfollow"})
        self.client.force_login(self.owner)
        self.client.post(reverse("comment_create", args=[self.ticket.pk]), {"body": "Update"})
        self.assertFalse(Notification.objects.exists())
        self.ticket.is_hidden = True
        self.ticket.save()
        self.assertEqual(self.client.get(reverse("notifications")).status_code, 200)
