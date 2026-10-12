from django.contrib import admin

from .models import Comment, Project, Ticket


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
