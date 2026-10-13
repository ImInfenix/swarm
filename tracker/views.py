from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import CommentForm, ContentReportForm, ProjectEditForm, ProjectForm, ProjectVersionForm, SignUpForm, TicketForm, TriageForm
from .account import revoke_user_access
from .middleware import LANGUAGE_COOKIE
from .models import ApiToken, Comment, ContentReport, Notification, Project, ProjectVersion, Ticket, TicketSubscription, TicketVote, UserPreference
from .notifications import notify_subscribers
from .rate_limits import allow_action, client_address
from .ticket_queries import filter_tickets, with_vote_counts


def home(request):
    projects = Project.objects.select_related("owner").annotate(ticket_count=Count("tickets")).order_by("name")[:6]
    tickets = with_vote_counts(Ticket.objects.filter(is_hidden=False).select_related("project", "author")).order_by("-created_at", "-pk")[:8]
    return render(request, "tracker/home.html", {"projects": projects, "tickets": tickets})


def project_list(request):
    projects = Project.objects.select_related("owner").annotate(ticket_count=Count("tickets")).order_by("name", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        projects = projects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    page = Paginator(projects, 12).get_page(request.GET.get("page"))
    return render(request, "tracker/project_list.html", {"projects": page, "page": page, "query": query})


def project_detail(request, slug):
    project = get_object_or_404(Project.objects.select_related("owner"), slug=slug)
    tickets, filters, filter_query = filter_tickets(project.tickets.filter(is_hidden=False).select_related("author", "project"), request.GET)
    popular_tickets = with_vote_counts(project.tickets.filter(is_hidden=False, duplicate_of__isnull=True, status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]).select_related("project")).filter(vote_count__gt=0).order_by("-vote_count", "-updated_at", "-pk")[:3]
    page = Paginator(tickets, 20).get_page(request.GET.get("page"))
    return render(request, "tracker/project_detail.html", {
        "project": project,
        "versions": project.versions.all(),
        "tickets": page,
        "page": page,
        "status": filters["status"],
        "priority": filters["priority"],
        "ticket_type": filters["type"],
        "version": filters["version"],
        "sort": filters["sort"],
        "query": filters["query"],
        "filter_query": filter_query,
        "popular_tickets": popular_tickets,
        "types": Ticket.Type.choices,
        "statuses": Ticket.Status.choices,
        "priorities": Ticket.Priority.choices,
    })


@login_required
def project_create(request):
    if request.method == "POST" and not allow_action("project", request.user.pk, 5, 86400):
        return HttpResponse(_("Too many requests. Try again later."), status=429)
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        messages.success(request, _("Project created."))
        return redirect(project)
    return render(request, "tracker/form.html", {"form": form, "title": _("New project"), "submit_label": _("Create project")})


@login_required
def project_edit(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.user != project.owner and not request.user.is_staff:
        raise PermissionDenied
    form = ProjectEditForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Project updated."))
        return redirect(project)
    return render(request, "tracker/form.html", {"form": form, "title": _("Edit project"), "submit_label": _("Save changes")})


@login_required
def project_version_create(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.user != project.owner and not request.user.is_staff:
        raise PermissionDenied
    form = ProjectVersionForm(request.POST or None)
    form.instance.project = project
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Version created."))
        return redirect(project)
    return render(request, "tracker/form.html", {"form": form, "title": _("Add version"), "submit_label": _("Add version")})


@login_required
def project_version_edit(request, slug, pk):
    project = get_object_or_404(Project, slug=slug)
    if request.user != project.owner and not request.user.is_staff:
        raise PermissionDenied
    version = get_object_or_404(ProjectVersion, project=project, pk=pk)
    form = ProjectVersionForm(request.POST or None, instance=version)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Version updated."))
        return redirect(project)
    return render(request, "tracker/form.html", {"form": form, "title": _("Edit version"), "submit_label": _("Save changes")})


@login_required
def project_triage_dashboard(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.user != project.owner and not request.user.is_staff:
        raise PermissionDenied
    tickets = with_vote_counts(project.tickets.filter(is_hidden=False, duplicate_of__isnull=True).select_related("project"))
    popular = tickets.filter(status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS], vote_count__gt=0).order_by("-vote_count", "-updated_at", "-pk")[:10]
    bugs = tickets.filter(type=Ticket.Type.BUG, status=Ticket.Status.OPEN).order_by("-created_at", "-pk")[:10]
    unanswered = tickets.filter(status=Ticket.Status.OPEN, comments__isnull=True).order_by("-created_at", "-pk")[:10]
    return render(request, "tracker/triage_dashboard.html", {"project": project, "popular": popular, "bugs": bugs, "unanswered": unanswered})


def ticket_list(request):
    tickets, filters, filter_query = filter_tickets(Ticket.objects.filter(is_hidden=False).select_related("project", "author"), request.GET, allow_project=True)
    page = Paginator(tickets, 20).get_page(request.GET.get("page"))
    return render(request, "tracker/ticket_list.html", {"tickets": page, "page": page, "query": filters["query"], "status": filters["status"], "priority": filters["priority"], "ticket_type": filters["type"], "sort": filters["sort"], "project_slug": filters["project"], "filter_query": filter_query, "statuses": Ticket.Status.choices, "types": Ticket.Type.choices})


@login_required
def ticket_create(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == "POST" and not allow_action("ticket", request.user.pk, 10, 3600):
        return HttpResponse(_("Too many requests. Try again later."), status=429)
    form = TicketForm(request.POST or None, project=project)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.project = project
        ticket.author = request.user
        ticket.save()
        messages.success(request, _("Ticket created."))
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": _("New ticket · %(project)s") % {"project": project.name}, "submit_label": _("Create ticket"), "ticket_form": True, "related_project": project})


def ticket_detail(request, pk):
    ticket = get_object_or_404(with_vote_counts(Ticket.objects.filter(is_hidden=False).select_related("project", "project__owner", "author", "affected_version", "target_version", "fixed_version", "duplicate_of")), pk=pk)
    comments = ticket.comments.filter(is_hidden=False).select_related("author")
    voted = request.user.is_authenticated and TicketVote.objects.filter(ticket=ticket, user=request.user).exists()
    subscribed = request.user.is_authenticated and TicketSubscription.objects.filter(ticket=ticket, user=request.user).exists()
    return render(request, "tracker/ticket_detail.html", {"ticket": ticket, "comments": comments, "comment_form": CommentForm(), "voted": voted, "subscribed": subscribed})


@login_required
@require_POST
def ticket_subscription(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_hidden=False)
    if request.POST.get("action") == "follow":
        TicketSubscription.objects.get_or_create(ticket=ticket, user=request.user)
    elif request.POST.get("action") == "unfollow":
        TicketSubscription.objects.filter(ticket=ticket, user=request.user).delete()
    else:
        return HttpResponseBadRequest(_("Unknown subscription action."))
    return redirect(ticket)


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user, ticket__is_hidden=False).select_related("ticket", "actor")
    page = Paginator(notifications, 20).get_page(request.GET.get("page"))
    return render(request, "tracker/notifications.html", {"notifications": page, "page": page})


@login_required
@require_POST
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user, ticket__is_hidden=False)
    Notification.objects.filter(pk=notification.pk, read_at__isnull=True).update(read_at=timezone.now())
    return redirect(notification.ticket)


@login_required
@require_POST
def ticket_vote(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_hidden=False)
    if ticket.duplicate_of_id and request.POST.get("action") != "remove":
        return HttpResponseBadRequest(_("Vote on the original ticket."))
    if not allow_action("vote", request.user.pk, 120, 3600):
        return HttpResponse(_("Too many requests. Try again later."), status=429)
    action = request.POST.get("action")
    if action == "add":
        TicketVote.objects.get_or_create(ticket=ticket, user=request.user)
    elif action == "remove":
        TicketVote.objects.filter(ticket=ticket, user=request.user).delete()
    else:
        return HttpResponseBadRequest(_("Unknown vote action."))
    return redirect(ticket)


@login_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user != ticket.author and not request.user.is_staff:
        raise PermissionDenied
    form = TicketForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Ticket updated."))
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": _("Edit ticket"), "submit_label": _("Save changes"), "ticket_form": True})


@login_required
def ticket_triage(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("project"), pk=pk)
    if request.user != ticket.project.owner and not request.user.is_staff:
        raise PermissionDenied
    previous = (ticket.status, ticket.priority, ticket.target_version_id, ticket.fixed_version_id, ticket.duplicate_of_id)
    form = TriageForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        current = (ticket.status, ticket.priority, ticket.target_version_id, ticket.fixed_version_id, ticket.duplicate_of_id)
        if current != previous:
            notify_subscribers(ticket, request.user, Notification.Kind.TRIAGE)
        messages.success(request, _("Triage updated."))
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": _("Triage ticket"), "submit_label": _("Save changes")})


@login_required
@require_POST
def comment_create(request, pk):
    ticket = get_object_or_404(with_vote_counts(Ticket.objects.filter(is_hidden=False)), pk=pk)
    if not allow_action("comment", request.user.pk, 30, 3600):
        return HttpResponse(_("Too many requests. Try again later."), status=429)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
        Ticket.objects.filter(pk=ticket.pk).update(updated_at=timezone.now())
        notify_subscribers(ticket, request.user, Notification.Kind.COMMENT)
        messages.success(request, _("Comment added."))
        return redirect(ticket)
    comments = ticket.comments.filter(is_hidden=False).select_related("author")
    voted = TicketVote.objects.filter(ticket=ticket, user=request.user).exists()
    subscribed = TicketSubscription.objects.filter(ticket=ticket, user=request.user).exists()
    return render(request, "tracker/ticket_detail.html", {"ticket": ticket, "comments": comments, "comment_form": form, "voted": voted, "subscribed": subscribed}, status=400)


def submit_content_report(request, target, ticket, title):
    if request.method == "POST" and not allow_action("report", request.user.pk, 10, 3600):
        return HttpResponse(_("Too many requests. Try again later."), status=429)
    form = ContentReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ContentReport.objects.get_or_create(reporter=request.user, defaults=form.cleaned_data, **target)
        messages.success(request, _("Report received."))
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": title, "submit_label": _("Send report")})


@login_required
def ticket_report(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_hidden=False)
    return submit_content_report(request, {"ticket": ticket}, ticket, _("Report ticket"))


@login_required
def comment_report(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("ticket"), pk=pk, is_hidden=False, ticket__is_hidden=False)
    return submit_content_report(request, {"comment": comment}, comment.ticket, _("Report comment"))


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST" and not allow_action("signup", client_address(request), 5, 3600):
        return HttpResponse(_("Too many requests. Try again later."), status=429)
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserPreference.objects.create(user=user, language=request.LANGUAGE_CODE)
        login(request, user)
        messages.success(request, _("Account created."))
        return redirect("home")
    return render(request, "tracker/form.html", {"form": form, "title": _("Create an account"), "submit_label": _("Sign up")})


class RateLimitedLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        if not allow_action("login", client_address(request), 20, 300):
            return HttpResponse(_("Too many requests. Try again later."), status=429)
        return super().post(request, *args, **kwargs)


@login_required
def account(request):
    form = PasswordChangeForm(request.user)
    return render(request, "tracker/account.html", {"password_form": form})


@login_required
@require_POST
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST)
    if not form.is_valid():
        return render(request, "tracker/account.html", {"password_form": form}, status=400)
    user = form.save()
    ApiToken.objects.filter(user=user).delete()
    update_session_auth_hash(request, user)
    messages.success(request, _("Password changed."))
    return redirect("account")


@login_required
@require_POST
def logout_all(request):
    if request.POST.get("confirm") != "logout":
        return HttpResponseBadRequest(_("Confirmation required."))
    with transaction.atomic():
        revoke_user_access(request.user)
    logout(request)
    messages.success(request, _("Signed out on all devices."))
    return redirect("home")


@login_required
@require_POST
def delete_account(request):
    if request.POST.get("confirm") != "delete":
        return HttpResponseBadRequest(_("Confirmation required."))
    with transaction.atomic():
        revoke_user_access(request.user)
        request.user.delete()
    logout(request)
    messages.success(request, _("Account deleted."))
    return redirect("home")


@require_POST
def set_language(request):
    language = request.POST.get("language", "")
    if language not in dict(settings.LANGUAGES):
        return HttpResponseBadRequest(_("Unsupported language."))
    if request.user.is_authenticated:
        UserPreference.objects.update_or_create(user=request.user, defaults={"language": language})
    target = request.POST.get("next") or reverse("home")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=not settings.DEBUG):
        target = reverse("home")
    response = redirect(target)
    response.set_cookie(LANGUAGE_COOKIE, language, max_age=365 * 24 * 60 * 60, secure=not settings.DEBUG, httponly=True, samesite="Lax")
    return response
