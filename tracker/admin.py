from django.contrib import admin

from django.utils import timezone

from .models import ApiToken, Comment, ContentReport, Project, ProjectVersion, Ticket, TicketVote, UserPreference


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "language")
    search_fields = ("user__username",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "description", "owner__username")
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "type", "status", "priority", "author", "created_at")
    list_filter = ("type", "status", "priority", "project", "is_hidden")
    search_fields = ("title", "description", "project__name")
    readonly_fields = ("created_at", "updated_at")
    actions = ("hide_tickets", "show_tickets")

    @admin.action(description="Hide selected tickets")
    def hide_tickets(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description="Show selected tickets")
    def show_tickets(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(ProjectVersion)
class ProjectVersionAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "released_on", "created_at")
    list_filter = ("project",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "is_hidden", "created_at")
    search_fields = ("body", "ticket__title", "author__username")
    readonly_fields = ("created_at",)
    actions = ("hide_comments", "show_comments")

    @admin.action(description="Hide selected comments")
    def hide_comments(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description="Show selected comments")
    def show_comments(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "reporter", "ticket", "comment", "created_at", "resolved_at")
    list_filter = ("reason", "resolved_at")
    readonly_fields = ("reporter", "ticket", "comment", "reason", "details", "created_at")
    actions = ("resolve_reports",)

    @admin.action(description="Mark selected reports as resolved")
    def resolve_reports(self, request, queryset):
        queryset.update(resolved_at=timezone.now())

    def has_add_permission(self, request):
        return False


@admin.register(TicketVote)
class TicketVoteAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")
    readonly_fields = ("ticket", "user", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "digest", "created_at", "expires_at")

    def has_add_permission(self, request):
        return False
