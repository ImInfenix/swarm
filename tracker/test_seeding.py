from datetime import datetime, timezone
from io import StringIO
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from .models import Comment, Notification, Project, ProjectVersion, Ticket, TicketAttachment, TicketSubscription, TicketVote


class DemoCommandsTests(TransactionTestCase):
    def setUp(self):
        temporary = TemporaryDirectory(dir=settings.BASE_DIR)
        self.addCleanup(temporary.cleanup)
        media_settings = override_settings(MEDIA_ROOT=temporary.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def test_seed_is_repeatable_and_reset_clears_content(self):
        models = (get_user_model(), Project, ProjectVersion, Ticket, TicketVote, Comment, TicketAttachment, TicketSubscription, Notification)

        call_command("seed_demo", stdout=StringIO())
        self.assertEqual([model.objects.count() for model in models], [4, 2, 5, 8, 19, 4, 1, 9, 4])
        self.assertFalse(get_user_model().objects.get(username="demo-owner").has_usable_password())
        ticket = Ticket.objects.get(title="The map stays blurry after returning from the pause menu")
        attachment = ticket.attachments.get()
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))
        self.assertEqual(ticket.target_version.name, "1.2")
        self.assertEqual(ticket.created_at, datetime(2025, 3, 11, 14, 10, tzinfo=timezone.utc))
        self.assertEqual(ticket.updated_at, datetime(2025, 3, 12, 9, 15, tzinfo=timezone.utc))
        self.assertTrue(all(comment.ticket.created_at <= comment.created_at <= comment.ticket.updated_at for comment in Comment.objects.select_related("ticket")))
        self.assertEqual(Ticket.objects.get(title="The harbor overview overlaps the settings menu").status, Ticket.Status.NEEDS_INFO)
        self.assertEqual(Ticket.objects.get(title="Show the production rate in building details").closure_reason, Ticket.ClosureReason.DECLINED)

        call_command("seed_demo", stdout=StringIO())
        self.assertEqual([model.objects.count() for model in models], [4, 2, 5, 8, 19, 4, 1, 9, 4])
        ticket.refresh_from_db()
        self.assertEqual(ticket.updated_at, datetime(2025, 3, 12, 9, 15, tzinfo=timezone.utc))

        call_command("reset_demo", yes=True, stdout=StringIO(), stderr=StringIO())
        self.assertTrue(all(not model.objects.exists() for model in models))
        self.assertFalse(attachment.file.storage.exists(attachment.file.name))

    def test_local_login_option(self):
        output = StringIO()
        with override_settings(DEBUG=True):
            call_command("seed_demo", enable_login=True, stdout=output)
        password = output.getvalue().split("Password: ", 1)[1].strip()
        self.assertTrue(get_user_model().objects.get(username="demo-owner").check_password(password))
        self.assertTrue(get_user_model().objects.get(username="demo-alex").check_password(password))
        self.assertTrue(self.client.login(username="demo-alex", password=password))
        self.assertContains(self.client.get(reverse("notifications")), "The map stays blurry")
        ticket = Ticket.objects.get(title="The map stays blurry after returning from the pause menu")
        self.assertContains(self.client.get(ticket.get_absolute_url()), "map-blur.png")
        attachment_response = self.client.get(reverse("ticket_attachment_download", args=[ticket.attachments.get().pk]))
        self.assertEqual(attachment_response.status_code, 200)
        attachment_response.close()
        suggestions = self.client.get(reverse("api_ticket_suggestions", args=["skybound"]), {"q": "map stays blurry"}).json()
        self.assertIn(ticket.pk, [item["id"] for item in suggestions])
        self.assertContains(self.client.get(reverse("project_roadmap", args=["skybound"])), "1.2")
        self.client.logout()
        self.assertTrue(self.client.login(username="demo-owner", password=password))
        needs_info = Ticket.objects.get(title="The harbor overview overlaps the settings menu")
        self.assertEqual(self.client.get(reverse("ticket_triage", args=[needs_info.pk])).status_code, 200)
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command("seed_demo", enable_login=True, stdout=StringIO())
