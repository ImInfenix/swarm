from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .api_auth import issue_api_token
from .models import ApiToken, Comment, Project, Ticket


class AccountFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="member", email="member@example.com", password="old-strong-password-123")
        self.project = Project.objects.create(name="Demo", slug="demo", owner=self.user)
        self.ticket = Ticket.objects.create(project=self.project, author=self.user, title="Issue", description="Details")
        self.comment = Comment.objects.create(ticket=self.ticket, author=self.user, body="A reply")

    def test_account_page_requires_login_and_shows_confirmation_dialog(self):
        self.assertRedirects(self.client.get(reverse("account")), f"{reverse('login')}?next={reverse('account')}")
        self.client.force_login(self.user)
        response = self.client.get(reverse("account"))
        self.assertContains(response, "Change password")
        self.assertContains(response, 'id="password-toggle" aria-controls="password-panel" aria-expanded="false"')
        self.assertContains(response, 'id="password-panel" class="password-panel" hidden')
        self.assertContains(response, "Sign out all devices")
        self.assertContains(response, '<dialog id="logout-all-dialog"')
        self.assertContains(response, 'data-open-logout-all')
        self.assertContains(response, 'data-close-logout-all')
        self.assertContains(response, 'name="confirm" value="logout"')
        self.assertContains(response, '/static/tracker/account.js?v=2')
        self.assertContains(response, '<dialog id="delete-account-dialog"')
        self.assertContains(response, 'class="button button-danger"')
        self.assertEqual(self.client.get(reverse("delete_account")).status_code, 405)
        self.client.post(reverse("set_language"), {"language": "fr"})
        translated = self.client.get(reverse("account"))
        self.assertContains(translated, "Mon compte")
        self.assertContains(translated, "Déconnecter tous les appareils")
        self.assertContains(translated, "Annuler")

    def test_password_change_requires_current_password_and_revokes_api_tokens(self):
        self.client.force_login(self.user)
        other_client = Client()
        other_client.force_login(self.user)
        issue_api_token(self.user)
        data = {"old_password": "wrong", "new_password1": "new-strong-password-456", "new_password2": "new-strong-password-456"}
        invalid_response = self.client.post(reverse("change_password"), data)
        self.assertEqual(invalid_response.status_code, 400)
        self.assertContains(invalid_response, 'id="password-toggle" aria-controls="password-panel" aria-expanded="true"', status_code=400)
        self.assertContains(invalid_response, 'id="password-panel" class="password-panel"', status_code=400)
        self.assertNotContains(invalid_response, 'id="password-panel" class="password-panel" hidden', status_code=400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-strong-password-123"))
        self.assertEqual(ApiToken.objects.filter(user=self.user).count(), 1)
        data["old_password"] = "old-strong-password-123"
        self.assertRedirects(self.client.post(reverse("change_password"), data), reverse("account"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-strong-password-456"))
        self.assertEqual(self.client.get(reverse("account")).status_code, 200)
        self.assertRedirects(other_client.get(reverse("account")), f"{reverse('login')}?next={reverse('account')}")
        self.assertFalse(ApiToken.objects.filter(user=self.user).exists())

    def test_sign_out_everywhere_revokes_all_sessions_and_tokens(self):
        self.client.force_login(self.user)
        other_client = Client()
        other_client.force_login(self.user)
        token, _ = issue_api_token(self.user)
        api_client = APIClient()
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(api_client.get(reverse("api_me")).status_code, 200)
        self.assertEqual(self.client.post(reverse("logout_all")).status_code, 400)
        self.assertEqual(self.client.get(reverse("account")).status_code, 200)
        self.assertEqual(api_client.get(reverse("api_me")).status_code, 200)
        self.assertRedirects(self.client.post(reverse("logout_all"), {"confirm": "logout"}), reverse("home"))
        self.assertRedirects(self.client.get(reverse("account")), f"{reverse('login')}?next={reverse('account')}")
        self.assertRedirects(other_client.get(reverse("account")), f"{reverse('login')}?next={reverse('account')}")
        self.assertEqual(api_client.get(reverse("api_me")).status_code, 401)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_account_deletion_requires_confirmation_and_preserves_content(self):
        self.client.force_login(self.user)
        token, _ = issue_api_token(self.user)
        self.assertEqual(self.client.post(reverse("delete_account")).status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertRedirects(self.client.post(reverse("delete_account"), {"confirm": "delete"}), reverse("home"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.project.refresh_from_db()
        self.ticket.refresh_from_db()
        self.comment.refresh_from_db()
        self.assertIsNone(self.project.owner)
        self.assertIsNone(self.ticket.author)
        self.assertIsNone(self.comment.author)
        self.assertContains(self.client.get(reverse("project_detail", args=["demo"])), "Deleted account")
        self.assertContains(self.client.get(reverse("ticket_detail", args=[self.ticket.pk])), "Deleted account")
        self.assertEqual(self.client.get(reverse("account")).status_code, 302)
        self.assertEqual(self.client.get(reverse("api_project_detail", args=["demo"])).json()["owner"], None)
        api_client = APIClient()
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(api_client.get(reverse("api_me")).status_code, 401)

    def test_sensitive_web_actions_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse("logout_all")).status_code, 403)
        self.assertEqual(client.post(reverse("delete_account"), {"confirm": "delete"}).status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(client.get(reverse("account")).status_code, 200)

    def test_api_account_actions(self):
        token, _ = issue_api_token(self.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        password_url = reverse("api_password")
        body = {"old_password": "wrong", "new_password1": "new-strong-password-456", "new_password2": "new-strong-password-456"}
        self.assertEqual(client.post(password_url, body, format="json").status_code, 400)
        self.assertEqual(client.get(reverse("api_me")).status_code, 200)
        body["old_password"] = "old-strong-password-123"
        self.assertEqual(client.post(password_url, body, format="json").status_code, 200)
        self.assertEqual(client.get(reverse("api_me")).status_code, 401)
        self.assertFalse(ApiToken.objects.filter(user=self.user).exists())
        client.credentials()
        login = client.post(reverse("api_token"), {"username": "member", "password": "new-strong-password-456"}, format="json")
        self.assertEqual(login.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
        self.assertEqual(client.post(reverse("api_logout_all"), {}, format="json").status_code, 204)
        self.assertEqual(client.get(reverse("api_me")).status_code, 401)
        token, _ = issue_api_token(self.user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.delete(reverse("api_me")).status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.project.refresh_from_db()
        self.assertIsNone(self.project.owner)
