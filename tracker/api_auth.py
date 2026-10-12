import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import ApiToken


def issue_api_token(user):
    value = secrets.token_urlsafe(32)
    token = ApiToken.objects.create(
        user=user,
        digest=hashlib.sha256(value.encode("ascii")).hexdigest(),
        expires_at=timezone.now() + timedelta(days=30),
    )
    return value, token


class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != b"bearer":
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Jeton invalide.")
        try:
            value = parts[1].decode("ascii")
        except UnicodeDecodeError as error:
            raise AuthenticationFailed("Jeton invalide.") from error
        digest = hashlib.sha256(value.encode("ascii")).hexdigest()
        token = ApiToken.objects.select_related("user").filter(digest=digest, expires_at__gt=timezone.now()).first()
        if token is None or not token.user.is_active:
            raise AuthenticationFailed("Jeton invalide ou expiré.")
        return token.user, token

    def authenticate_header(self, request):
        return "Bearer"
