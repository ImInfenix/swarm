from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework import serializers, status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_auth import issue_api_token
from .account import revoke_user_access
from .forms import SignUpForm
from .models import ApiToken, Comment, Project, ProjectVersion, Ticket, TicketVote, UserPreference, normalize_project_name
from .ticket_queries import filter_tickets


class ApiPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    language = serializers.SerializerMethodField()

    def get_language(self, user):
        preference = UserPreference.objects.filter(user=user).first()
        return preference.language if preference else "en"


class StrictModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise ValidationError({field: [_("Unsupported field.")] for field in sorted(unknown)})
        return super().to_internal_value(data)


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()

    def get_owner(self, project):
        return project.owner.username if project.owner else None

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
            raise ValidationError(_("The name cannot exceed 80 characters."))
        return name


class ProjectVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectVersion
        fields = ("id", "name", "released_on", "created_at")


class ProjectVersionWriteSerializer(StrictModelSerializer):
    class Meta:
        model = ProjectVersion
        fields = ("name", "released_on")

    def validate_name(self, value):
        project = self.context["project"]
        versions = ProjectVersion.objects.filter(project=project, name__iexact=value)
        if self.instance:
            versions = versions.exclude(pk=self.instance.pk)
        if versions.exists():
            raise ValidationError(_("This version already exists in the project."))
        return value

    def validate_released_on(self, value):
        if self.instance and not value and self.instance.fixed_tickets.exists():
            raise ValidationError(_("This version is already marked as a released fix."))
        return value


class TicketSerializer(serializers.ModelSerializer):
    project = serializers.CharField(source="project.slug", read_only=True)
    author = serializers.CharField(source="author.username", read_only=True)
    vote_count = serializers.SerializerMethodField()

    def get_vote_count(self, ticket):
        return ticket.vote_count if hasattr(ticket, "vote_count") else ticket.votes.count()

    class Meta:
        model = Ticket
        fields = ("id", "project", "type", "title", "description", "steps_to_reproduce", "expected_result", "actual_result", "affected_version", "target_version", "fixed_version", "status", "priority", "vote_count", "author", "created_at", "updated_at")


class TicketWriteSerializer(StrictModelSerializer):
    class Meta:
        model = Ticket
        fields = ("type", "title", "description", "steps_to_reproduce", "expected_result", "actual_result", "affected_version")

    def validate(self, attrs):
        project = self.instance.project if self.instance else self.context["project"]
        affected_version = attrs.get("affected_version", self.instance.affected_version if self.instance else None)
        if affected_version and affected_version.project_id != project.pk:
            raise ValidationError({"affected_version": _("Choose a version from this project.")})
        ticket_type = attrs.get("type", self.instance.type if self.instance else Ticket.Type.UNCLASSIFIED)
        if ticket_type == Ticket.Type.BUG:
            errors = {}
            for field in ("steps_to_reproduce", "expected_result", "actual_result"):
                value = attrs.get(field, getattr(self.instance, field, ""))
                if not value.strip():
                    errors[field] = _("This field is required for bug reports.")
            if errors:
                raise ValidationError(errors)
        else:
            attrs.update({"steps_to_reproduce": "", "expected_result": "", "actual_result": "", "affected_version": None})
        return attrs


class TriageSerializer(StrictModelSerializer):
    class Meta:
        model = Ticket
        fields = ("status", "priority", "target_version", "fixed_version")

    def validate(self, attrs):
        for field in ("target_version", "fixed_version"):
            version = attrs.get(field)
            if version and version.project_id != self.instance.project_id:
                raise ValidationError({field: _("Choose a version from this project.")})
        fixed_version = attrs.get("fixed_version")
        if fixed_version and not fixed_version.released_on:
            raise ValidationError({"fixed_version": _("Choose a released version.")})
        return attrs


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
                {"method": "GET", "path": "/api/v1/auth/me/", "access": "token", "returns": ["id", "username", "email", "language"]},
                {"method": "PATCH", "path": "/api/v1/auth/me/", "access": "token", "body": ["language"], "values": {"language": ["en", "fr"]}},
                {"method": "DELETE", "path": "/api/v1/auth/me/", "access": "token", "description": "Delete the account and anonymize its contributions."},
                {"method": "POST", "path": "/api/v1/auth/password/", "access": "token", "body": ["old_password", "new_password1", "new_password2"], "description": "Change the password and revoke all API tokens."},
                {"method": "POST", "path": "/api/v1/auth/logout-all/", "access": "token", "description": "Revoke all sessions and API tokens."},
                {"method": "GET", "path": "/api/v1/projects/", "access": "public", "query": ["q", "page", "page_size"], "returns": "paginated projects"},
                {"method": "POST", "path": "/api/v1/projects/", "access": "token", "body": ["name", "description"], "description": "The slug is generated from the name and limited to 10 characters."},
                {"method": "GET", "path": "/api/v1/projects/{slug}/", "access": "public", "returns": ["id", "name", "slug", "description", "owner", "created_at", "updated_at"]},
                {"method": "PATCH", "path": "/api/v1/projects/{slug}/", "access": "owner or staff", "body": ["name", "description"]},
                {"method": "GET", "path": "/api/v1/projects/{slug}/versions/", "access": "public", "returns": ["id", "name", "released_on", "created_at"]},
                {"method": "POST", "path": "/api/v1/projects/{slug}/versions/", "access": "owner or staff", "body": ["name", "released_on"]},
                {"method": "PATCH", "path": "/api/v1/projects/{slug}/versions/{id}/", "access": "owner or staff", "body": ["name", "released_on"]},
                {"method": "GET", "path": "/api/v1/projects/{slug}/tickets/", "access": "public", "query": ["q", "status", "priority", "type", "version", "sort", "page", "page_size"], "values": {"sort": ["newest", "popular", "active"]}, "returns": "paginated tickets with vote_count"},
                {"method": "POST", "path": "/api/v1/projects/{slug}/tickets/", "access": "token", "body": ["type", "title", "description", "steps_to_reproduce", "expected_result", "actual_result", "affected_version"], "values": {"type": Ticket.Type.values}},
                {"method": "GET", "path": "/api/v1/tickets/", "access": "public", "query": ["q", "status", "priority", "type", "version", "sort", "project", "page", "page_size"], "values": {"sort": ["newest", "popular", "active"]}, "returns": "paginated tickets with vote_count"},
                {"method": "GET", "path": "/api/v1/tickets/{id}/", "access": "public", "returns": ["id", "project", "type", "title", "description", "affected_version", "target_version", "fixed_version", "status", "priority", "vote_count", "author", "created_at", "updated_at"]},
                {"method": "PATCH", "path": "/api/v1/tickets/{id}/", "access": "author or staff", "body": ["type", "title", "description", "steps_to_reproduce", "expected_result", "actual_result", "affected_version"]},
                {"method": "PUT", "path": "/api/v1/tickets/{id}/vote/", "access": "token", "description": "Add one vote for the authenticated user."},
                {"method": "DELETE", "path": "/api/v1/tickets/{id}/vote/", "access": "token", "description": "Remove the authenticated user's vote."},
                {"method": "PATCH", "path": "/api/v1/tickets/{id}/triage/", "access": "project owner or staff", "body": ["status", "priority", "target_version", "fixed_version"], "values": {"status": Ticket.Status.values, "priority": Ticket.Priority.values}},
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
            raise ValidationError({"detail": _("Expected a JSON object.")})
        form = SignUpForm(request.data)
        if not form.is_valid():
            raise ValidationError({field: list(errors) for field, errors in form.errors.items()})
        with transaction.atomic():
            user = form.save()
            UserPreference.objects.create(user=user, language=request.LANGUAGE_CODE)
            value, token = issue_api_token(user)
        return Response({"user": UserSerializer(user).data, "token": value, "expires_at": token.expires_at}, status=status.HTTP_201_CREATED)


class TokenApi(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "authentication"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": _("Expected a JSON object.")})
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValidationError({"detail": _("Invalid credentials.")})
        user = authenticate(request=request._request, username=username, password=password)
        if user is None:
            raise ValidationError({"detail": _("Invalid credentials.")})
        UserPreference.objects.get_or_create(user=user, defaults={"language": request.LANGUAGE_CODE})
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

    def patch(self, request):
        if not isinstance(request.data, dict) or set(request.data) != {"language"}:
            raise ValidationError({"language": _("Provide a language: en or fr.")})
        language = request.data["language"]
        if language not in ("en", "fr"):
            raise ValidationError({"language": _("Provide a language: en or fr.")})
        UserPreference.objects.update_or_create(user=request.user, defaults={"language": language})
        translation.activate(language)
        request._request.LANGUAGE_CODE = language
        return Response(UserSerializer(request.user).data)

    def delete(self, request):
        with transaction.atomic():
            revoke_user_access(request.user)
            request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": _("Expected a JSON object.")})
        form = PasswordChangeForm(request.user, request.data)
        if not form.is_valid():
            raise ValidationError({field: list(errors) for field, errors in form.errors.items()})
        user = form.save()
        ApiToken.objects.filter(user=user).delete()
        return Response({"detail": _("Password changed. Sign in again to use the API.")})


class LogoutAllApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            revoke_user_access(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class ProjectVersionListApi(APIView):
    def get_project(self, slug):
        return get_object_or_404(Project.objects.select_related("owner"), slug=slug)

    def get(self, request, slug):
        project = self.get_project(slug)
        return Response(ProjectVersionSerializer(project.versions.all(), many=True).data)

    def post(self, request, slug):
        project = self.get_project(slug)
        if request.user != project.owner and not request.user.is_staff:
            raise PermissionDenied()
        serializer = ProjectVersionWriteSerializer(data=request.data, context={"project": project})
        serializer.is_valid(raise_exception=True)
        version = serializer.save(project=project)
        return Response(ProjectVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class ProjectVersionDetailApi(APIView):
    def patch(self, request, slug, pk):
        project = get_object_or_404(Project.objects.select_related("owner"), slug=slug)
        if request.user != project.owner and not request.user.is_staff:
            raise PermissionDenied()
        version = get_object_or_404(ProjectVersion, project=project, pk=pk)
        serializer = ProjectVersionWriteSerializer(version, data=request.data, partial=True, context={"project": project})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectVersionSerializer(version).data)


class ProjectTicketListApi(APIView):
    def get_project(self, slug):
        return get_object_or_404(Project, slug=slug)

    def get(self, request, slug):
        project = self.get_project(slug)
        tickets, _, _ = filter_tickets(project.tickets.filter(is_hidden=False).select_related("project", "author"), request.query_params)
        paginator = ApiPagination()
        page = paginator.paginate_queryset(tickets, request, view=self)
        return paginator.get_paginated_response(TicketSerializer(page, many=True).data)

    def post(self, request, slug):
        project = self.get_project(slug)
        serializer = TicketWriteSerializer(data=request.data, context={"project": project})
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(project=project, author=request.user)
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class TicketListApi(APIView):
    def get(self, request):
        tickets, _, _ = filter_tickets(Ticket.objects.filter(is_hidden=False).select_related("project", "author"), request.query_params, allow_project=True)
        paginator = ApiPagination()
        page = paginator.paginate_queryset(tickets, request, view=self)
        return paginator.get_paginated_response(TicketSerializer(page, many=True).data)


class TicketDetailApi(APIView):
    def get_object(self, pk):
        return get_object_or_404(Ticket.objects.filter(is_hidden=False).select_related("project", "author").annotate(vote_count=Count("votes")), pk=pk)

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


class TicketVoteApi(APIView):
    def get_ticket(self, pk):
        return get_object_or_404(Ticket, pk=pk, is_hidden=False)

    def put(self, request, pk):
        ticket = self.get_ticket(pk)
        TicketVote.objects.get_or_create(ticket=ticket, user=request.user)
        return Response({"vote_count": ticket.votes.count(), "voted": True})

    def delete(self, request, pk):
        ticket = self.get_ticket(pk)
        TicketVote.objects.filter(ticket=ticket, user=request.user).delete()
        return Response({"vote_count": ticket.votes.count(), "voted": False})


class TicketTriageApi(APIView):
    def patch(self, request, pk):
        ticket = get_object_or_404(Ticket.objects.filter(is_hidden=False).select_related("project", "project__owner", "author"), pk=pk)
        if request.user != ticket.project.owner and not request.user.is_staff:
            raise PermissionDenied()
        serializer = TriageSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketSerializer(ticket).data)


class CommentListApi(APIView):
    def get_ticket(self, pk):
        return get_object_or_404(Ticket, pk=pk, is_hidden=False)

    def get(self, request, pk):
        ticket = self.get_ticket(pk)
        comments = ticket.comments.filter(is_hidden=False).select_related("author").order_by("created_at", "pk")
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
