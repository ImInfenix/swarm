import warnings
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _
from PIL import Image, UnidentifiedImageError

from .models import Ticket, TicketAttachment


MAX_ATTACHMENTS = 3
MAX_FILE_SIZE = 5 * 1024 * 1024
IMAGE_TYPES = {"PNG": (".png", "image/png"), "JPEG": (".jpg", "image/jpeg"), "GIF": (".gif", "image/gif"), "WEBP": (".webp", "image/webp")}


def validate_attachments(ticket_type, uploads, existing_count=0):
    if not uploads:
        return []
    if ticket_type != Ticket.Type.BUG:
        raise ValidationError(_("Images can only be attached to bug reports."))
    if existing_count + len(uploads) > MAX_ATTACHMENTS:
        raise ValidationError(_("A bug report can have at most three images."))
    validated = []
    for uploaded in uploads:
        if not uploaded.size or uploaded.size > MAX_FILE_SIZE:
            raise ValidationError(_("Each image must be smaller than 5 MB."))
        original_name = Path(uploaded.name.replace("\\", "/")).name[:120]
        extension = Path(original_name).suffix.lower()
        if extension == ".jpeg":
            extension = ".jpg"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(uploaded)
                image_format = image.format
                dimensions = image.size
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise ValidationError(_("Upload a valid PNG, JPEG, GIF, or WebP image."))
        finally:
            uploaded.seek(0)
        if image_format not in IMAGE_TYPES or extension != IMAGE_TYPES[image_format][0] or max(dimensions) > 8000:
            raise ValidationError(_("Upload a valid PNG, JPEG, GIF, or WebP image."))
        validated.append((uploaded, original_name, IMAGE_TYPES[image_format][1]))
    return validated


def attach_files(ticket, uploads, user):
    with transaction.atomic():
        Ticket.objects.select_for_update().get(pk=ticket.pk)
        files = validate_attachments(ticket.type, uploads, ticket.attachments.count())
        created = []
        pending = None
        try:
            for uploaded, original_name, content_type in files:
                pending = TicketAttachment(ticket=ticket, original_name=original_name, content_type=content_type, uploaded_by=user)
                pending.file.save(original_name, uploaded, save=True)
                created.append(pending)
                pending = None
        except Exception:
            if pending and pending.file:
                pending.file.delete(save=False)
            for attachment in created:
                attachment.file.delete(save=False)
            raise
        return created
