import hashlib
import re
import unicodedata
from itertools import count

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.urls import reverse
from django.utils.text import slugify


def validate_project_name(value):
    if not value or any(unicodedata.category(character)[0] not in {"L", "N"} and character not in {" ", "-"} for character in value):
        raise ValidationError("Utilisez uniquement des lettres, des chiffres, des espaces ou des traits d'union.")
    if not any(unicodedata.category(character)[0] in {"L", "N"} for character in value):
        raise ValidationError("Le nom doit contenir une lettre ou un chiffre.")


def normalize_project_name(value):
    return re.sub(" +", " ", unicodedata.normalize("NFKC", value)).strip()


def project_slug_base(name):
    base = slugify(name)[:10].strip("-")
    return base or "p" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:9]


def project_slug_candidate(base, index):
    suffix = "" if index == 1 else f"-{index}"
    if len(suffix) >= 10:
        raise ValidationError("Impossible de générer une adresse unique pour ce projet.")
    return f"{base[:10 - len(suffix)].rstrip('-')}{suffix}"


class Project(models.Model):
    name = models.CharField(max_length=80, validators=[validate_project_name])
    slug = models.SlugField(max_length=10, unique=True, blank=True, editable=False)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("project_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if self.slug:
            return super().save(*args, **kwargs)
        base = project_slug_base(self.name)
        for index in count(1):
            candidate = project_slug_candidate(base, index)
            if type(self).objects.filter(slug=candidate).exists():
                continue
            self.slug = candidate
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if not type(self).objects.filter(slug=candidate).exists():
                    raise


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        IN_PROGRESS = "in_progress", "En cours"
        RESOLVED = "resolved", "Résolu"
        CLOSED = "closed", "Fermé"

    class Priority(models.TextChoices):
        LOW = "low", "Faible"
        NORMAL = "normal", "Normale"
        HIGH = "high", "Élevée"
        URGENT = "urgent", "Urgente"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tickets")
    title = models.CharField(max_length=160)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("ticket_detail", kwargs={"pk": self.pk})


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="comments")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on ticket {self.ticket_id}"


class ApiToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens")
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
