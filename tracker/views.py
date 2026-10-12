from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import CommentForm, ProjectEditForm, ProjectForm, SignUpForm, TicketForm, TriageForm
from .account import revoke_user_access
from .middleware import LANGUAGE_COOKIE
from .models import ApiToken, Project, Ticket, UserPreference


def home(request):
    projects = Project.objects.select_related("owner").annotate(ticket_count=Count("tickets")).order_by("name")[:6]
    tickets = Ticket.objects.select_related("project", "author").order_by("-created_at", "-pk")[:8]
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
    tickets = project.tickets.select_related("author").order_by("-created_at", "-pk")
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    if status in Ticket.Status.values:
        tickets = tickets.filter(status=status)
    else:
        status = ""
    if priority in Ticket.Priority.values:
        tickets = tickets.filter(priority=priority)
    else:
        priority = ""
    page = Paginator(tickets, 20).get_page(request.GET.get("page"))
    return render(request, "tracker/project_detail.html", {
        "project": project,
        "tickets": page,
        "page": page,
        "status": status,
        "priority": priority,
        "statuses": Ticket.Status.choices,
        "priorities": Ticket.Priority.choices,
    })


@login_required
def project_create(request):
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


def ticket_list(request):
    tickets = Ticket.objects.select_related("project", "author").order_by("-created_at", "-pk")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        tickets = tickets.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(project__name__icontains=query))
    if status in Ticket.Status.values:
        tickets = tickets.filter(status=status)
    else:
        status = ""
    page = Paginator(tickets, 20).get_page(request.GET.get("page"))
    return render(request, "tracker/ticket_list.html", {"tickets": page, "page": page, "query": query, "status": status, "statuses": Ticket.Status.choices})


@login_required
def ticket_create(request, slug):
    project = get_object_or_404(Project, slug=slug)
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.project = project
        ticket.author = request.user
        ticket.save()
        messages.success(request, _("Ticket created."))
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": _("New ticket · %(project)s") % {"project": project.name}, "submit_label": _("Create ticket")})


def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("project", "project__owner", "author"), pk=pk)
    comments = ticket.comments.select_related("author")
    return render(request, "tracker/ticket_detail.html", {"ticket": ticket, "comments": comments, "comment_form": CommentForm()})


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
    return render(request, "tracker/form.html", {"form": form, "title": _("Edit ticket"), "submit_label": _("Save changes")})


@login_required
def ticket_triage(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("project"), pk=pk)
    if request.user != ticket.project.owner and not request.user.is_staff:
        raise PermissionDenied
    form = TriageForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Triage updated."))
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": _("Triage ticket"), "submit_label": _("Save changes")})


@login_required
@require_POST
def comment_create(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
        Ticket.objects.filter(pk=ticket.pk).update(updated_at=timezone.now())
        messages.success(request, _("Comment added."))
        return redirect(ticket)
    comments = ticket.comments.select_related("author")
    return render(request, "tracker/ticket_detail.html", {"ticket": ticket, "comments": comments, "comment_form": form}, status=400)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserPreference.objects.create(user=user, language=request.LANGUAGE_CODE)
        login(request, user)
        messages.success(request, _("Account created."))
        return redirect("home")
    return render(request, "tracker/form.html", {"form": form, "title": _("Create an account"), "submit_label": _("Sign up")})


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
