from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, ProjectEditForm, ProjectForm, SignUpForm, TicketForm, TriageForm
from .models import Project, Ticket


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
        messages.success(request, "Projet créé.")
        return redirect(project)
    return render(request, "tracker/form.html", {"form": form, "title": "Nouveau projet", "submit_label": "Créer le projet"})


@login_required
def project_edit(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.user != project.owner and not request.user.is_staff:
        raise PermissionDenied
    form = ProjectEditForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Projet mis à jour.")
        return redirect(project)
    return render(request, "tracker/form.html", {"form": form, "title": "Modifier le projet", "submit_label": "Enregistrer"})


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
        messages.success(request, "Ticket créé.")
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": f"Nouveau ticket · {project.name}", "submit_label": "Créer le ticket"})


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
        messages.success(request, "Ticket mis à jour.")
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": "Modifier le ticket", "submit_label": "Enregistrer"})


@login_required
def ticket_triage(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("project"), pk=pk)
    if request.user != ticket.project.owner and not request.user.is_staff:
        raise PermissionDenied
    form = TriageForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Traitement mis à jour.")
        return redirect(ticket)
    return render(request, "tracker/form.html", {"form": form, "title": "Traiter le ticket", "submit_label": "Enregistrer"})


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
        messages.success(request, "Commentaire ajouté.")
        return redirect(ticket)
    comments = ticket.comments.select_related("author")
    return render(request, "tracker/ticket_detail.html", {"ticket": ticket, "comments": comments, "comment_form": form}, status=400)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Compte créé.")
        return redirect("home")
    return render(request, "tracker/form.html", {"form": form, "title": "Créer un compte", "submit_label": "S'inscrire"})
