import hashlib
import ipaddress

from django.conf import settings
from django.core.cache import cache


def client_address(request):
    remote = request.META.get("REMOTE_ADDR", "")
    trusted = set(settings.SWARM_TRUSTED_PROXY_IPS)
    if remote not in trusted:
        return remote
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    for candidate in reversed(forwarded.split(",")):
        candidate = candidate.strip()
        try:
            address = str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
        if address not in trusted:
            return address
    return remote


def allow_action(action, identity, limit, window_seconds):
    digest = hashlib.sha256(f"{action}:{identity}".encode("utf-8")).hexdigest()
    key = f"swarm:rate:{digest}"
    if cache.add(key, 1, timeout=window_seconds):
        return True
    try:
        count = cache.incr(key)
    except ValueError:
        return cache.add(key, 1, timeout=window_seconds)
    return count <= limit
