from django.contrib import admin

from .models import ApiToken, Comment, Project, Ticket


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "description", "owner__username")
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "status", "priority", "author", "created_at")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description", "project__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "created_at")
    search_fields = ("body", "ticket__title", "author__username")
    readonly_fields = ("created_at",)


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "digest", "created_at", "expires_at")

    def has_add_permission(self, request):
        return False
