from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Project, Ticket, UserPreference


class LanguageFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="member", password="strong-test-password")
        self.project = Project.objects.create(name="Demo", slug="demo", owner=self.user)
        self.ticket = Ticket.objects.create(project=self.project, author=self.user, title="Example", description="Details")

    def test_english_is_default_and_french_is_available_to_visitors(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "Welcome to Swarm")
        self.assertContains(response, 'name="language" value="en" lang="en" aria-label="English" aria-current="true">EN</button>')
        self.assertContains(response, 'name="language" value="fr" lang="fr" aria-label="Français" >FR</button>')
        self.assertNotContains(response, 'language-select')
        response = self.client.post(reverse("set_language"), {"language": "fr", "next": reverse("home")})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(response.cookies["swarm_language"].value, "fr")
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, "Bienvenue sur Swarm")
        self.assertContains(response, 'name="language" value="fr" lang="fr" aria-label="Français" aria-current="true">FR</button>')
        self.assertContains(response, "1 ticket")
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertContains(response, "Ouvert")
        self.assertEqual(response.headers["Content-Language"], "fr")

    def test_account_preference_survives_new_session(self):
        self.client.force_login(self.user)
        self.client.post(reverse("set_language"), {"language": "fr"})
        self.assertEqual(UserPreference.objects.get(user=self.user).language, "fr")
        another_client = Client()
        self.assertTrue(another_client.login(username="member", password="strong-test-password"))
        response = another_client.get(reverse("project_create"))
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, "Nouveau projet")
        self.assertContains(response, "Nom")
        another_client.post(reverse("set_language"), {"language": "en"})
        self.assertEqual(UserPreference.objects.get(user=self.user).language, "en")
        self.assertContains(self.client.get(reverse("home")), "Welcome to Swarm")

    def test_new_account_keeps_language_chosen_before_signup(self):
        self.client.post(reverse("set_language"), {"language": "fr"})
        response = self.client.post(reverse("signup"), {
            "username": "new-member",
            "email": "new@example.com",
            "password1": "long-and-unique-password-123",
            "password2": "long-and-unique-password-123",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(UserPreference.objects.get(user__username="new-member").language, "fr")

    def test_invalid_language_and_external_redirect_are_rejected(self):
        response = self.client.post(reverse("set_language"), {"language": "de"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("swarm_language", response.cookies)
        response = self.client.post(reverse("set_language"), {"language": "fr", "next": "https://example.com/"})
        self.assertRedirects(response, reverse("home"))

    def test_api_profile_updates_language_and_uses_it_for_errors(self):
        client = APIClient()
        login = client.post(reverse("api_token"), {"username": "member", "password": "strong-test-password"}, format="json")
        self.assertEqual(login.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
        updated = client.patch(reverse("api_me"), {"language": "fr"}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["language"], "fr")
        self.assertEqual(client.get(reverse("api_me")).data["language"], "fr")
        invalid = client.patch(reverse("api_me"), {"language": "de"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("Indiquez une langue", str(invalid.data["language"]))
        self.assertEqual(UserPreference.objects.get(user=self.user).language, "fr")
        self.assertEqual(client.get(reverse("api_me")).headers["Content-Language"], "fr")
