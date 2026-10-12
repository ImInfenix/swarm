from django.contrib.sessions.models import Session
from django.utils import timezone

from .models import ApiToken


def revoke_user_access(user):
    user_id = str(user.pk)
    session_keys = [
        session.session_key
        for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator()
        if session.get_decoded().get("_auth_user_id") == user_id
    ]
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()
    ApiToken.objects.filter(user=user).delete()
