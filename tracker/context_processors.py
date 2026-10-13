from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}
    return {"unread_notification_count": Notification.objects.filter(user=request.user, read_at__isnull=True, ticket__is_hidden=False).count()}
