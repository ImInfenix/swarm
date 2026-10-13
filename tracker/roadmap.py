from django.db.models import Prefetch, Q

from .models import ProjectVersion, Ticket
from .ticket_queries import with_vote_counts


def project_roadmap(project):
    visible = with_vote_counts(
        Ticket.objects.filter(is_hidden=False, duplicate_of__isnull=True)
        .select_related("project", "author")
        .prefetch_related("attachments")
    )
    versions = list(
        ProjectVersion.objects.filter(project=project).prefetch_related(
            Prefetch("target_tickets", queryset=visible.filter(fixed_version__isnull=True).exclude(status=Ticket.Status.CLOSED).order_by("-created_at", "-pk"), to_attr="planned_tickets"),
            Prefetch("fixed_tickets", queryset=visible.order_by("-created_at", "-pk"), to_attr="delivered_tickets"),
        )
    )
    planned = [version for version in versions if version.released_on is None]
    released = sorted((version for version in versions if version.released_on), key=lambda version: (version.released_on, version.pk), reverse=True)
    backlog = visible.filter(
        Q(target_version__isnull=True) | Q(target_version__released_on__isnull=False),
        fixed_version__isnull=True,
        status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS, Ticket.Status.NEEDS_INFO],
    ).order_by("-created_at", "-pk")
    return planned, released, backlog
