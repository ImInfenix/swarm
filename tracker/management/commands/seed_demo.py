import secrets
from datetime import datetime, timezone
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw

from tracker.attachments import attach_files
from tracker.models import Comment, Notification, Project, ProjectVersion, Ticket, TicketAttachment, TicketSubscription, TicketVote, UserPreference


def demo_screenshot():
    image = Image.new("RGB", (640, 360), "#243a4d")
    draw = ImageDraw.Draw(image)
    draw.rectangle((35, 45, 605, 315), fill="#8aaea2")
    draw.rectangle((65, 75, 575, 285), fill="#c9d8bc")
    draw.ellipse((250, 100, 390, 240), fill="#79a88f")
    draw.text((80, 90), "Skybound map", fill="#243a4d")
    draw.text((80, 260), "Map remains blurry after pause", fill="#243a4d")
    output = BytesIO()
    image.save(output, format="PNG")
    return SimpleUploadedFile("map-blur.png", output.getvalue(), content_type="image/png")


class Command(BaseCommand):
    help = "Create or update demonstration data for the feedback workflow."

    def add_arguments(self, parser):
        parser.add_argument("--enable-login", action="store_true", help="Generate a shared password for demonstration accounts in local debug mode.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["enable_login"] and not settings.DEBUG:
            raise CommandError("Demo login can only be enabled in local debug mode.")
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

        demo_password = None
        if options["enable_login"]:
            demo_password = secrets.token_urlsafe(18)
            for user in users.values():
                user.set_password(demo_password)
                user.save(update_fields=["password"])

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
            ("skybound", "1.1", "2025-08-20"),
            ("skybound", "1.2", None),
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
                "author": "demo-alex", "affected_version": "1.0", "target_version": "1.2",
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
                "author": "demo-camille", "target_version": "1.2",
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
                "author": "demo-alex", "closure_reason": Ticket.ClosureReason.DECLINED,
                "decision_note": "The production rate is already available in the building details.",
                "voters": [], "comments": [],
            },
            {
                "project": "clockwork", "title": "The harbor overview overlaps the settings menu",
                "description": "On narrow screens, the harbor overview covers the settings menu.",
                "type": Ticket.Type.BUG, "status": Ticket.Status.NEEDS_INFO, "priority": Ticket.Priority.NORMAL,
                "created_at": datetime(2025, 10, 6, 7, 55, tzinfo=timezone.utc),
                "updated_at": datetime(2025, 10, 6, 7, 55, tzinfo=timezone.utc),
                "author": "demo-jules", "affected_version": "0.9", "voters": ["demo-camille"], "comments": [],
                "decision_note": "Which screen width and browser are you using?",
            },
        ]

        tickets = {}
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
                    "closure_reason": data.get("closure_reason", ""),
                    "decision_note": data.get("decision_note", ""),
                    "steps_to_reproduce": data.get("steps_to_reproduce", ""),
                    "expected_result": data.get("expected_result", ""),
                    "actual_result": data.get("actual_result", ""),
                },
            )
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
            tickets[(data["project"], data["title"])] = ticket
            TicketSubscription.objects.get_or_create(ticket=ticket, user=users[data["author"]])
            for username in data["voters"]:
                TicketVote.objects.get_or_create(ticket=ticket, user=users[username])
            for username, body, created_at in data["comments"]:
                comment, _ = Comment.objects.get_or_create(ticket=ticket, author=users[username], body=body)
                Comment.objects.filter(pk=comment.pk).update(created_at=created_at)

        map_ticket = tickets[("skybound", "The map stays blurry after returning from the pause menu")]
        TicketSubscription.objects.get_or_create(ticket=map_ticket, user=users["demo-jules"])
        attachment = TicketAttachment.objects.filter(ticket=map_ticket, original_name="map-blur.png", uploaded_by=users["demo-alex"]).first()
        if attachment and not attachment.file.storage.exists(attachment.file.name):
            attachment.delete()
            attachment = None
        if not attachment:
            attach_files(map_ticket, [demo_screenshot()], users["demo-alex"])

        notification_data = [
            ("skybound", "The map stays blurry after returning from the pause menu", "demo-camille", "demo-alex", Notification.Kind.COMMENT),
            ("skybound", "The map stays blurry after returning from the pause menu", "demo-camille", "demo-jules", Notification.Kind.COMMENT),
            ("skybound", "Add a photo mode for island views", "demo-owner", "demo-camille", Notification.Kind.COMMENT),
            ("clockwork", "The harbor overview overlaps the settings menu", "demo-owner", "demo-jules", Notification.Kind.TRIAGE),
        ]
        for project_slug, title, actor_name, recipient_name, kind in notification_data:
            Notification.objects.get_or_create(
                ticket=tickets[(project_slug, title)],
                actor=users[actor_name],
                user=users[recipient_name],
                kind=kind,
            )

        self.stdout.write(self.style.SUCCESS("Demonstration data is ready."))
        if demo_password:
            self.stdout.write(f"Demo login: demo-owner, demo-alex, demo-camille, demo-jules\nPassword: {demo_password}")
