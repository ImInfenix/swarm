from io import BytesIO
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from .api_auth import issue_api_token
from .models import Project, Ticket, TicketAttachment


def screenshot(name="screen.png"):
    output = BytesIO()
    Image.new("RGB", (2, 2), "red").save(output, "PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class TicketAttachmentTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(dir=settings.BASE_DIR)
        self.addCleanup(temporary.cleanup)
        media_settings = override_settings(MEDIA_ROOT=temporary.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.author = User.objects.create_user(username="author", password="test-password-123")
        self.other = User.objects.create_user(username="other", password="test-password-123")
        self.project = Project.objects.create(name="Demo", owner=self.other)
        self.data = {"type": "bug", "title": "Broken screen", "description": "Details", "steps_to_reproduce": "Open", "expected_result": "Visible", "actual_result": "Blank"}

    def test_web_create_download_and_delete(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse("ticket_create", args=[self.project.slug]), {**self.data, "attachments": [screenshot()]})
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get()
        attachment = TicketAttachment.objects.get(ticket=ticket)
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))
        self.assertContains(self.client.get(ticket.get_absolute_url()), "screen.png")
        download = self.client.get(reverse("ticket_attachment_download", args=[attachment.pk]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "image/png")
        download.close()
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("ticket_attachment_delete", args=[attachment.pk])).status_code, 302)
        self.assertFalse(attachment.file.storage.exists(attachment.file.name))

    def test_invalid_and_excess_uploads_do_not_create_tickets(self):
        self.client.force_login(self.author)
        url = reverse("ticket_create", args=[self.project.slug])
        invalid = SimpleUploadedFile("bad.png", b"<script>alert(1)</script>", content_type="image/png")
        self.assertContains(self.client.post(url, {**self.data, "attachments": [invalid]}), "Upload a valid PNG")
        self.assertFalse(Ticket.objects.exists())
        self.assertContains(self.client.post(url, {**self.data, "attachments": [screenshot(str(i) + ".png") for i in range(4)]}), "at most three")
        self.assertFalse(Ticket.objects.exists())
        feature = {"type": "feature", "title": "Idea", "description": "Details", "attachments": [screenshot()]}
        self.assertContains(self.client.post(url, feature), "only be attached to bug reports")
        self.assertFalse(Ticket.objects.exists())

    def test_api_upload_limit_permissions_and_hidden_download(self):
        ticket = Ticket.objects.create(project=self.project, author=self.author, **self.data)
        owner_token, _ = issue_api_token(self.author)
        other_token, _ = issue_api_token(self.other)
        client = APIClient()
        url = reverse("api_ticket_attachments", args=[ticket.pk])
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token}")
        self.assertEqual(client.post(url, {"file": screenshot()}, format="multipart").status_code, 403)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token}")
        for index in range(3):
            response = client.post(url, {"file": screenshot(str(index) + ".png")}, format="multipart")
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(client.post(url, {"file": screenshot("extra.png")}, format="multipart").status_code, 400)
        self.assertEqual(ticket.attachments.count(), 3)
        attachment = ticket.attachments.first()
        ticket.is_hidden = True
        ticket.save()
        self.assertEqual(self.client.get(reverse("ticket_attachment_download", args=[attachment.pk])).status_code, 404)
