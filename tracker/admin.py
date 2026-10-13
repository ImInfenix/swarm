from django.contrib import admin

from .models import ApiToken, Comment, Project, ProjectVersion, Ticket, TicketVote, UserPreference


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


@admin.register(ProjectVersion)
class ProjectVersionAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "released_on", "created_at")
    list_filter = ("project",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "created_at")
    search_fields = ("body", "ticket__title", "author__username")
    readonly_fields = ("created_at",)


@admin.register(TicketVote)
class TicketVoteAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")
    readonly_fields = ("ticket", "user", "created_at")


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "digest", "created_at", "expires_at")

    def has_add_permission(self, request):
        return False
