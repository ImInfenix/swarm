from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Comment, Project, Ticket, normalize_project_name


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label=_("Email address"))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This email address is already in use."))
        return email


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description")
        labels = {"name": _("Name"), "description": _("Description")}
        help_texts = {"name": _("The address is generated from the name (up to 10 characters). Use only letters, numbers, spaces, and hyphens.")}
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_name(self):
        name = normalize_project_name(self.cleaned_data["name"])
        if len(name) > 80:
            raise forms.ValidationError(_("The name cannot exceed 80 characters."))
        return name


class ProjectEditForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description")
        labels = {"name": _("Name"), "description": _("Description")}
        help_texts = {"name": _("The project address stays the same when you change its name.")}
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    clean_name = ProjectForm.clean_name


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("title", "description")
        labels = {"title": _("Title"), "description": _("Description")}
        widgets = {"description": forms.Textarea(attrs={"rows": 9})}


class TriageForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("status", "priority")
        labels = {"status": _("Status"), "priority": _("Priority")}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        labels = {"body": _("Your comment")}
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
