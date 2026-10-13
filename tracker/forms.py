from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Comment, Project, ProjectVersion, Ticket, normalize_project_name


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
        fields = ("type", "title", "description", "steps_to_reproduce", "expected_result", "actual_result", "affected_version")
        labels = {
            "type": _("Type"),
            "title": _("Title"),
            "description": _("Description"),
            "steps_to_reproduce": _("Steps to reproduce"),
            "expected_result": _("Expected result"),
            "actual_result": _("Actual result"),
            "affected_version": _("Affected version"),
        }
        help_texts = {"description": _("Describe the problem or explain why this feature would be useful.")}
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "steps_to_reproduce": forms.Textarea(attrs={"rows": 4}),
            "expected_result": forms.Textarea(attrs={"rows": 3}),
            "actual_result": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project or self.instance.project
        types = [(Ticket.Type.BUG, Ticket.Type.BUG.label), (Ticket.Type.FEATURE, Ticket.Type.FEATURE.label)]
        if self.instance.pk and self.instance.type == Ticket.Type.UNCLASSIFIED:
            types.insert(0, (Ticket.Type.UNCLASSIFIED, Ticket.Type.UNCLASSIFIED.label))
        self.fields["type"].choices = [("", _("Choose a type")), *types]
        self.fields["affected_version"].queryset = ProjectVersion.objects.filter(project=self.project)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("type") == Ticket.Type.BUG:
            for field in ("steps_to_reproduce", "expected_result", "actual_result"):
                if not cleaned.get(field, "").strip():
                    self.add_error(field, _("This field is required for bug reports."))
        else:
            for field in ("steps_to_reproduce", "expected_result", "actual_result", "affected_version"):
                cleaned[field] = None if field == "affected_version" else ""
        return cleaned


class ProjectVersionForm(forms.ModelForm):
    class Meta:
        model = ProjectVersion
        fields = ("name", "released_on")
        labels = {"name": _("Version"), "released_on": _("Release date")}
        help_texts = {"released_on": _("Leave empty while this version is planned.")}
        widgets = {"released_on": forms.DateInput(attrs={"type": "date"})}

    def clean_name(self):
        name = self.cleaned_data["name"]
        versions = ProjectVersion.objects.filter(project=self.instance.project, name__iexact=name)
        if self.instance.pk:
            versions = versions.exclude(pk=self.instance.pk)
        if versions.exists():
            raise forms.ValidationError(_("This version already exists in the project."))
        return name

    def clean_released_on(self):
        released_on = self.cleaned_data["released_on"]
        if self.instance.pk and not released_on and self.instance.fixed_tickets.exists():
            raise forms.ValidationError(_("This version is already marked as a released fix."))
        return released_on


class TriageForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("status", "priority", "target_version", "fixed_version")
        labels = {"status": _("Status"), "priority": _("Priority"), "target_version": _("Target version"), "fixed_version": _("Released in version")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        versions = ProjectVersion.objects.filter(project=self.instance.project)
        self.fields["target_version"].queryset = versions
        self.fields["fixed_version"].queryset = versions.filter(released_on__isnull=False)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        labels = {"body": _("Your comment")}
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
