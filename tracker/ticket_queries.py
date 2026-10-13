from urllib.parse import urlencode

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from .models import Ticket, TicketVote


SORT_ORDERS = {
    "newest": ("-created_at", "-pk"),
    "popular": ("-vote_count", "-updated_at", "-pk"),
    "active": ("-updated_at", "-pk"),
}


def with_vote_counts(queryset):
    totals = (TicketVote.objects.annotate(canonical_ticket_id=Coalesce("ticket__duplicate_of_id", "ticket_id"))
              .filter(canonical_ticket_id=OuterRef("pk"))
              .order_by()
              .values("canonical_ticket_id")
              .annotate(total=Count("user_id", distinct=True))
              .values("total")[:1])
    return queryset.annotate(vote_count=Coalesce(Subquery(totals, output_field=IntegerField()), Value(0)))


def filter_tickets(queryset, params, allow_project=False):
    filters = {
        "query": params.get("q", "").strip(),
        "status": params.get("status", ""),
        "priority": params.get("priority", ""),
        "type": params.get("type", ""),
        "version": params.get("version", ""),
        "sort": params.get("sort", "newest"),
    }
    if allow_project:
        filters["project"] = params.get("project", "")
    if filters["query"]:
        queryset = queryset.filter(Q(title__icontains=filters["query"]) | Q(description__icontains=filters["query"]) | Q(project__name__icontains=filters["query"]))
    for field, choices in (("status", Ticket.Status.values), ("priority", Ticket.Priority.values), ("type", Ticket.Type.values)):
        if filters[field] in choices:
            queryset = queryset.filter(**{field: filters[field]})
        else:
            filters[field] = ""
    if filters["version"].isdecimal():
        queryset = queryset.filter(affected_version_id=int(filters["version"]))
    else:
        filters["version"] = ""
    if allow_project and filters["project"]:
        queryset = queryset.filter(project__slug=filters["project"])
    if filters["sort"] not in SORT_ORDERS:
        filters["sort"] = "newest"
    queryset = with_vote_counts(queryset).order_by(*SORT_ORDERS[filters["sort"]])
    query_params = {"q" if key == "query" else key: value for key, value in filters.items() if value and not (key == "sort" and value == "newest")}
    return queryset, filters, urlencode(query_params)
