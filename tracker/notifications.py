from .models import Notification, TicketSubscription


def notify_subscribers(ticket, actor, kind):
    if ticket.is_hidden:
        return
    recipients = set(TicketSubscription.objects.filter(ticket=ticket).values_list("user_id", flat=True))
    if kind == Notification.Kind.COMMENT and ticket.status == ticket.Status.NEEDS_INFO and ticket.project.owner_id:
        recipients.add(ticket.project.owner_id)
    recipients.discard(actor.pk)
    Notification.objects.bulk_create(
        Notification(user_id=user_id, ticket=ticket, actor=actor, kind=kind)
        for user_id in recipients
    )
