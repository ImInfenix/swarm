from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers

from .models import UserPreference


LANGUAGE_COOKIE = "swarm_language"


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.COOKIES.get(LANGUAGE_COOKIE, settings.LANGUAGE_CODE)
        if language not in dict(settings.LANGUAGES):
            language = settings.LANGUAGE_CODE
        if request.user.is_authenticated:
            preference, _ = UserPreference.objects.get_or_create(user=request.user, defaults={"language": language})
            language = preference.language
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        response.headers["Content-Language"] = translation.get_language()
        patch_vary_headers(response, ("Cookie",))
        return response
