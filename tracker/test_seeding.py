from datetime import datetime, timezone
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TransactionTestCase

from .models import Comment, Project, ProjectVersion, Ticket, TicketVote


class DemoCommandsTests(TransactionTestCase):
    def test_seed_is_repeatable_and_reset_clears_content(self):
        models = (get_user_model(), Project, ProjectVersion, Ticket, TicketVote, Comment)

        call_command("seed_demo", stdout=StringIO())
        self.assertEqual([model.objects.count() for model in models], [4, 2, 4, 8, 19, 4])
        self.assertFalse(get_user_model().objects.get(username="demo-owner").has_usable_password())
        ticket = Ticket.objects.get(title="The map stays blurry after returning from the pause menu")
        self.assertEqual(ticket.created_at, datetime(2025, 3, 11, 14, 10, tzinfo=timezone.utc))
        self.assertEqual(ticket.updated_at, datetime(2025, 3, 12, 9, 15, tzinfo=timezone.utc))
        self.assertTrue(all(comment.ticket.created_at <= comment.created_at <= comment.ticket.updated_at for comment in Comment.objects.select_related("ticket")))

        call_command("seed_demo", stdout=StringIO())
        self.assertEqual([model.objects.count() for model in models], [4, 2, 4, 8, 19, 4])
        ticket.refresh_from_db()
        self.assertEqual(ticket.updated_at, datetime(2025, 3, 12, 9, 15, tzinfo=timezone.utc))

        call_command("reset_demo", yes=True, stdout=StringIO(), stderr=StringIO())
        self.assertTrue(all(not model.objects.exists() for model in models))
