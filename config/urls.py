from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from tracker import api, views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.ApiRoot.as_view(), name="api_root"),
    path("api/v1/auth/signup/", api.SignupApi.as_view(), name="api_signup"),
    path("api/v1/auth/token/", api.TokenApi.as_view(), name="api_token"),
    path("api/v1/auth/me/", api.MeApi.as_view(), name="api_me"),
    path("api/v1/projects/", api.ProjectListApi.as_view(), name="api_project_list"),
    path("api/v1/projects/<slug:slug>/", api.ProjectDetailApi.as_view(), name="api_project_detail"),
    path("api/v1/projects/<slug:slug>/tickets/", api.ProjectTicketListApi.as_view(), name="api_project_tickets"),
    path("api/v1/tickets/", api.TicketListApi.as_view(), name="api_ticket_list"),
    path("api/v1/tickets/<int:pk>/", api.TicketDetailApi.as_view(), name="api_ticket_detail"),
    path("api/v1/tickets/<int:pk>/triage/", api.TicketTriageApi.as_view(), name="api_ticket_triage"),
    path("api/v1/tickets/<int:pk>/comments/", api.CommentListApi.as_view(), name="api_ticket_comments"),
    path("", views.home, name="home"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<slug:slug>/", views.project_detail, name="project_detail"),
    path("projects/<slug:slug>/edit/", views.project_edit, name="project_edit"),
    path("projects/<slug:slug>/tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/edit/", views.ticket_edit, name="ticket_edit"),
    path("tickets/<int:pk>/triage/", views.ticket_triage, name="ticket_triage"),
    path("tickets/<int:pk>/comments/", views.comment_create, name="comment_create"),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
]
