from .models import Notification, TicketSubscription


def notify_subscribers(ticket, actor, kind):
    if ticket.is_hidden:
        return
    recipients = TicketSubscription.objects.filter(ticket=ticket).exclude(user_id=actor.pk).values_list("user_id", flat=True)
    Notification.objects.bulk_create(
        Notification(user_id=user_id, ticket=ticket, actor=actor, kind=kind)
        for user_id in recipients
    )
