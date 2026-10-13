import re

from django.db.models import Case, IntegerField, Q, Value, When

from .models import Ticket


def similar_tickets(project, query):
    words = list(dict.fromkeys(word for word in re.findall(r"\w+", query[:160].lower()) if len(word) >= 3))[:6]
    if not words:
        return Ticket.objects.none()
    tickets = Ticket.objects.filter(project=project, is_hidden=False, duplicate_of__isnull=True)
    for word in words:
        tickets = tickets.filter(Q(title__icontains=word) | Q(description__icontains=word))
    return tickets.annotate(
        match_rank=Case(When(title__icontains=query.strip(), then=Value(0)), default=Value(1), output_field=IntegerField())
    ).order_by("match_rank", "-created_at", "-pk")[:5]
