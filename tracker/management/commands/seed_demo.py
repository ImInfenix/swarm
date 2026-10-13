from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from tracker.models import Comment, Project, ProjectVersion, Ticket, TicketVote, UserPreference


class Command(BaseCommand):
    help = "Create or update the demonstration accounts, projects, tickets, votes, and comments."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        users = {}
        for username, email, language in [
            ("demo-owner", "demo-owner@example.com", "en"),
            ("demo-alex", "demo-alex@example.com", "en"),
            ("demo-camille", "demo-camille@example.com", "fr"),
            ("demo-jules", "demo-jules@example.com", "fr"),
        ]:
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_active": True},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            UserPreference.objects.update_or_create(user=user, defaults={"language": language})
            users[username] = user

        project_data = [
            ("skybound", "Skybound", "A small exploration game about floating islands.", "demo-owner"),
            ("clockwork", "Clockwork Harbor", "A strategy game about rebuilding a mechanical port.", "demo-owner"),
        ]
        projects = {}
        for slug, name, description, owner in project_data:
            project, _ = Project.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "description": description, "owner": users[owner]},
            )
            projects[slug] = project

        version_data = [
            ("skybound", "1.0", "2025-03-15"),
            ("skybound", "1.1", None),
            ("clockwork", "0.9", "2025-02-01"),
            ("clockwork", "1.0", None),
        ]
        versions = {}
        for slug, name, released_on in version_data:
            version, _ = ProjectVersion.objects.update_or_create(
                project=projects[slug],
                name=name,
                defaults={"released_on": released_on},
            )
            versions[(slug, name)] = version

        ticket_data = [
            {
                "project": "skybound", "title": "The map stays blurry after returning from the pause menu",
                "description": "The island map sometimes remains blurry after closing the pause menu.",
                "type": Ticket.Type.BUG, "status": Ticket.Status.OPEN, "priority": Ticket.Priority.HIGH,
                "created_at": datetime(2025, 3, 11, 14, 10, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 3, 12, 9, 15, tzinfo=timezone.utc),
                "author": "demo-alex", "affected_version": "1.0", "target_version": "1.1",
                "steps_to_reproduce": "Open the map, pause the game, then resume.",
                "expected_result": "The map should return to its normal focus.",
                "actual_result": "The map remains blurry until the area is reloaded.",
                "comments": [("demo-camille", "I can reproduce this on the desert island too.", datetime(2025, 3, 12, 9, 15, tzinfo=timezone.utc))],
                "voters": ["demo-camille", "demo-jules"],
            },
            {
                "project": "skybound", "title": "Add a photo mode for island views",
                "description": "A photo mode would make it easier to capture custom views of the islands.",
                "type": Ticket.Type.FEATURE, "status": Ticket.Status.IN_PROGRESS, "priority": Ticket.Priority.NORMAL,
                "created_at": datetime(2025, 4, 2, 9, 25, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 7, 18, 16, 40, tzinfo=timezone.utc),
                "author": "demo-camille", "target_version": "1.1",
                "comments": [("demo-owner", "This is planned for the next update.", datetime(2025, 7, 18, 16, 40, tzinfo=timezone.utc))],
                "voters": ["demo-alex", "demo-jules"],
            },
            {
                "project": "skybound", "title": "Controller hints do not update when changing layouts",
                "description": "The on-screen hints keep showing the default controller layout.",
                "type": Ticket.Type.BUG, "status": Ticket.Status.RESOLVED, "priority": Ticket.Priority.LOW,
                "created_at": datetime(2025, 5, 7, 11, 5, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 8, 21, 10, 15, tzinfo=timezone.utc),
                "author": "demo-jules", "affected_version": "1.0", "fixed_version": "1.1",
                "comments": [("demo-owner", "Fixed in the latest update.", datetime(2025, 8, 21, 10, 15, tzinfo=timezone.utc))], "voters": ["demo-alex"],
            },
            {
                "project": "skybound", "title": "Let players remap keyboard controls",
                "description": "Add an in-game screen for remapping keyboard controls.",
                "type": Ticket.Type.FEATURE, "status": Ticket.Status.OPEN, "priority": Ticket.Priority.NORMAL,
                "created_at": datetime(2025, 6, 19, 13, 50, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 6, 19, 13, 50, tzinfo=timezone.utc),
                "author": "demo-alex", "voters": ["demo-camille"], "comments": [],
            },
            {
                "project": "clockwork", "title": "Loading screen can freeze when a match ends",
                "description": "The loading screen can remain visible after a match ends.",
                "type": Ticket.Type.BUG, "status": Ticket.Status.IN_PROGRESS, "priority": Ticket.Priority.URGENT,
                "created_at": datetime(2025, 2, 14, 8, 35, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 9, 3, 15, 20, tzinfo=timezone.utc),
                "author": "demo-jules", "affected_version": "0.9", "target_version": "1.0",
                "steps_to_reproduce": "Finish a match while connected to a slow network.",
                "expected_result": "Return to the harbor after the match.",
                "actual_result": "The loading screen remains visible.",
                "comments": [("demo-owner", "We are checking the network reconnect flow.", datetime(2025, 9, 3, 15, 20, tzinfo=timezone.utc))],
                "voters": ["demo-alex", "demo-camille"],
            },
            {
                "project": "clockwork", "title": "Add a compact harbor overview",
                "description": "A compact overview would help compare building production at a glance.",
                "type": Ticket.Type.FEATURE, "status": Ticket.Status.OPEN, "priority": Ticket.Priority.HIGH,
                "created_at": datetime(2025, 7, 23, 17, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 7, 23, 17, 0, tzinfo=timezone.utc),
                "author": "demo-camille", "voters": ["demo-alex", "demo-jules"], "comments": [],
            },
            {
                "project": "clockwork", "title": "Show the production rate in building details",
                "description": "Include the current production rate on each building detail panel.",
                "type": Ticket.Type.FEATURE, "status": Ticket.Status.CLOSED, "priority": Ticket.Priority.LOW,
                "created_at": datetime(2025, 1, 29, 10, 40, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 4, 10, 12, 5, tzinfo=timezone.utc),
                "author": "demo-alex", "target_version": "1.0", "voters": [], "comments": [],
            },
            {
                "project": "clockwork", "title": "The harbor overview overlaps the settings menu",
                "description": "On narrow screens, the harbor overview covers the settings menu.",
                "type": Ticket.Type.BUG, "status": Ticket.Status.OPEN, "priority": Ticket.Priority.NORMAL,
                "created_at": datetime(2025, 10, 6, 7, 55, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 10, 6, 7, 55, tzinfo=timezone.utc),
                "author": "demo-jules", "affected_version": "0.9", "voters": ["demo-camille"], "comments": [],
            },
        ]

        for data in ticket_data:
            ticket, _ = Ticket.objects.update_or_create(
                project=projects[data["project"]],
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "type": data["type"],
                    "status": data["status"],
                    "priority": data["priority"],
                    "author": users[data["author"]],
                    "affected_version": versions.get((data["project"], data.get("affected_version"))),
                    "target_version": versions.get((data["project"], data.get("target_version"))),
                    "fixed_version": versions.get((data["project"], data.get("fixed_version"))),
                    "steps_to_reproduce": data.get("steps_to_reproduce", ""),
                    "expected_result": data.get("expected_result", ""),
                    "actual_result": data.get("actual_result", ""),
                },
            )
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
            for username in data["voters"]:
                TicketVote.objects.get_or_create(ticket=ticket, user=users[username])
            for username, body, created_at in data["comments"]:
                comment, _ = Comment.objects.get_or_create(ticket=ticket, author=users[username], body=body)
                Comment.objects.filter(pk=comment.pk).update(created_at=created_at)

        self.stdout.write(self.style.SUCCESS("Demonstration data is ready."))
