from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_auth import issue_api_token
from .forms import SignUpForm
from .models import Comment, Project, Ticket, normalize_project_name


class ApiPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class StrictModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise ValidationError({field: ["Champ non pris en charge."] for field in sorted(unknown)})
        return super().to_internal_value(data)


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Project
        fields = ("id", "name", "slug", "description", "owner", "created_at", "updated_at")


class ProjectWriteSerializer(StrictModelSerializer):
    class Meta:
        model = Project
        fields = ("name", "description")

    def validate_name(self, value):
        name = normalize_project_name(value)
        if len(name) > 80:
            raise ValidationError("Le nom ne peut pas dépasser 80 caractères.")
        return name


class TicketSerializer(serializers.ModelSerializer):
    project = serializers.CharField(source="project.slug", read_only=True)
    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "project", "title", "description", "status", "priority", "author", "created_at", "updated_at")


class TicketWriteSerializer(StrictModelSerializer):
    class Meta:
        model = Ticket
        fields = ("title", "description")


class TriageSerializer(StrictModelSerializer):
    class Meta:
        model = Ticket
        fields = ("status", "priority")


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author", "body", "created_at")


class CommentWriteSerializer(StrictModelSerializer):
    class Meta:
        model = Comment
        fields = ("body",)


class ApiRoot(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "name": "Swarm API",
            "version": "1",
            "base_path": "/api/v1/",
            "content_type": "application/json",
            "authentication": {
                "type": "Bearer token",
                "header": "Authorization: Bearer <token>",
                "lifetime_days": 30,
                "description": "Create a token with signup or login. Revoke it with DELETE /api/v1/auth/token/.",
            },
            "pagination": {
                "query": ["page", "page_size"],
                "max_page_size": 100,
                "response": ["count", "next", "previous", "results"],
            },
            "endpoints": [
                {"method": "POST", "path": "/api/v1/auth/signup/", "access": "public", "body": ["username", "email", "password1", "password2"], "returns": ["user", "token", "expires_at"]},
                {"method": "POST", "path": "/api/v1/auth/token/", "access": "public", "body": ["username", "password"], "returns": ["user", "token", "expires_at"]},
                {"method": "DELETE", "path": "/api/v1/auth/token/", "access": "token", "description": "Revoke the current token."},
                {"method": "GET", "path": "/api/v1/auth/me/", "access": "token", "returns": ["id", "username", "email"]},
                {"method": "GET", "path": "/api/v1/projects/", "access": "public", "query": ["q", "page", "page_size"], "returns": "paginated projects"},
                {"method": "POST", "path": "/api/v1/projects/", "access": "token", "body": ["name", "description"], "description": "The slug is generated from the name and limited to 10 characters."},
                {"method": "GET", "path": "/api/v1/projects/{slug}/", "access": "public", "returns": ["id", "name", "slug", "description", "owner", "created_at", "updated_at"]},
                {"method": "PATCH", "path": "/api/v1/projects/{slug}/", "access": "owner or staff", "body": ["name", "description"]},
                {"method": "GET", "path": "/api/v1/projects/{slug}/tickets/", "access": "public", "query": ["status", "priority", "page", "page_size"], "returns": "paginated tickets"},
                {"method": "POST", "path": "/api/v1/projects/{slug}/tickets/", "access": "token", "body": ["title", "description"]},
                {"method": "GET", "path": "/api/v1/tickets/", "access": "public", "query": ["q", "status", "priority", "project", "page", "page_size"], "returns": "paginated tickets"},
                {"method": "GET", "path": "/api/v1/tickets/{id}/", "access": "public", "returns": ["id", "project", "title", "description", "status", "priority", "author", "created_at", "updated_at"]},
                {"method": "PATCH", "path": "/api/v1/tickets/{id}/", "access": "author or staff", "body": ["title", "description"]},
                {"method": "PATCH", "path": "/api/v1/tickets/{id}/triage/", "access": "project owner or staff", "body": ["status", "priority"], "values": {"status": Ticket.Status.values, "priority": Ticket.Priority.values}},
                {"method": "GET", "path": "/api/v1/tickets/{id}/comments/", "access": "public", "query": ["page", "page_size"], "returns": "paginated comments"},
                {"method": "POST", "path": "/api/v1/tickets/{id}/comments/", "access": "token", "body": ["body"]},
            ],
            "errors": {"400": "Invalid input", "401": "Missing or invalid token", "403": "Insufficient permissions", "404": "Unknown resource", "429": "Authentication rate limit exceeded"},
        })


class SignupApi(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "authentication"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Objet JSON attendu."})
        form = SignUpForm(request.data)
        if not form.is_valid():
            raise ValidationError({field: list(errors) for field, errors in form.errors.items()})
        with transaction.atomic():
            user = form.save()
            value, token = issue_api_token(user)
        return Response({"user": UserSerializer(user).data, "token": value, "expires_at": token.expires_at}, status=status.HTTP_201_CREATED)


class TokenApi(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "authentication"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Objet JSON attendu."})
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValidationError({"detail": "Identifiants invalides."})
        user = authenticate(request=request._request, username=username, password=password)
        if user is None:
            raise ValidationError({"detail": "Identifiants invalides."})
        value, token = issue_api_token(user)
        return Response({"user": UserSerializer(user).data, "token": value, "expires_at": token.expires_at})

    def delete(self, request):
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProjectListApi(APIView):
    def get(self, request):
        projects = Project.objects.select_related("owner").order_by("name", "pk")
        query = request.query_params.get("q", "").strip()
        if query:
            projects = projects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        paginator = ApiPagination()
        page = paginator.paginate_queryset(projects, request, view=self)
        return paginator.get_paginated_response(ProjectSerializer(page, many=True).data)

    def post(self, request):
        serializer = ProjectWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(owner=request.user)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailApi(APIView):
    def get_object(self, slug):
        return get_object_or_404(Project.objects.select_related("owner"), slug=slug)

    def get(self, request, slug):
        return Response(ProjectSerializer(self.get_object(slug)).data)

    def patch(self, request, slug):
        project = self.get_object(slug)
        if request.user != project.owner and not request.user.is_staff:
            raise PermissionDenied()
        serializer = ProjectWriteSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectSerializer(project).data)


class ProjectTicketListApi(APIView):
    def get_project(self, slug):
        return get_object_or_404(Project, slug=slug)

    def get(self, request, slug):
        project = self.get_project(slug)
        tickets = project.tickets.select_related("project", "author").order_by("-created_at", "-pk")
        ticket_status = request.query_params.get("status", "")
        priority = request.query_params.get("priority", "")
        if ticket_status in Ticket.Status.values:
            tickets = tickets.filter(status=ticket_status)
        if priority in Ticket.Priority.values:
            tickets = tickets.filter(priority=priority)
        paginator = ApiPagination()
        page = paginator.paginate_queryset(tickets, request, view=self)
        return paginator.get_paginated_response(TicketSerializer(page, many=True).data)

    def post(self, request, slug):
        project = self.get_project(slug)
        serializer = TicketWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(project=project, author=request.user)
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class TicketListApi(APIView):
    def get(self, request):
        tickets = Ticket.objects.select_related("project", "author").order_by("-created_at", "-pk")
        query = request.query_params.get("q", "").strip()
        ticket_status = request.query_params.get("status", "")
        priority = request.query_params.get("priority", "")
        project = request.query_params.get("project", "")
        if query:
            tickets = tickets.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(project__name__icontains=query))
        if ticket_status in Ticket.Status.values:
            tickets = tickets.filter(status=ticket_status)
        if priority in Ticket.Priority.values:
            tickets = tickets.filter(priority=priority)
        if project:
            tickets = tickets.filter(project__slug=project)
        paginator = ApiPagination()
        page = paginator.paginate_queryset(tickets, request, view=self)
        return paginator.get_paginated_response(TicketSerializer(page, many=True).data)


class TicketDetailApi(APIView):
    def get_object(self, pk):
        return get_object_or_404(Ticket.objects.select_related("project", "author"), pk=pk)

    def get(self, request, pk):
        return Response(TicketSerializer(self.get_object(pk)).data)

    def patch(self, request, pk):
        ticket = self.get_object(pk)
        if request.user != ticket.author and not request.user.is_staff:
            raise PermissionDenied()
        serializer = TicketWriteSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketSerializer(ticket).data)


class TicketTriageApi(APIView):
    def patch(self, request, pk):
        ticket = get_object_or_404(Ticket.objects.select_related("project", "project__owner", "author"), pk=pk)
        if request.user != ticket.project.owner and not request.user.is_staff:
            raise PermissionDenied()
        serializer = TriageSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketSerializer(ticket).data)


class CommentListApi(APIView):
    def get_ticket(self, pk):
        return get_object_or_404(Ticket, pk=pk)

    def get(self, request, pk):
        ticket = self.get_ticket(pk)
        comments = ticket.comments.select_related("author").order_by("created_at", "pk")
        paginator = ApiPagination()
        page = paginator.paginate_queryset(comments, request, view=self)
        return paginator.get_paginated_response(CommentSerializer(page, many=True).data)

    def post(self, request, pk):
        ticket = self.get_ticket(pk)
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(ticket=ticket, author=request.user)
        Ticket.objects.filter(pk=ticket.pk).update(updated_at=timezone.now())
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
