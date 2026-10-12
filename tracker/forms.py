from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Comment, Project, Ticket


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="Adresse e-mail")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse est déjà utilisée.")
        return email


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "slug", "description")
        labels = {"name": "Nom", "slug": "Identifiant dans l'adresse", "description": "Description"}
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_slug(self):
        return self.cleaned_data["slug"].lower()


class ProjectEditForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description")
        labels = {"name": "Nom", "description": "Description"}
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("title", "description")
        labels = {"title": "Titre", "description": "Description"}
        widgets = {"description": forms.Textarea(attrs={"rows": 9})}


class TriageForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("status", "priority")
        labels = {"status": "État", "priority": "Priorité"}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        labels = {"body": "Votre commentaire"}
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
