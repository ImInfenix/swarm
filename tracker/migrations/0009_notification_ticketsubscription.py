import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def subscribe_existing_authors(apps, schema_editor):
    Ticket = apps.get_model("tracker", "Ticket")
    TicketSubscription = apps.get_model("tracker", "TicketSubscription")
    TicketSubscription.objects.bulk_create(
        TicketSubscription(ticket_id=ticket.pk, user_id=ticket.author_id)
        for ticket in Ticket.objects.exclude(author_id__isnull=True).iterator()
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0008_alter_ticket_type_ticket_valid_ticket_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('comment', 'New comment'), ('triage', 'Ticket updated')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_notifications', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='tracker.ticket')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at', '-pk'],
                'indexes': [models.Index(fields=['user', 'read_at', '-created_at'], name='notification_inbox_idx')],
            },
        ),
        migrations.CreateModel(
            name='TicketSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='tracker.ticket')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ticket_subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('ticket', 'user'), name='unique_ticket_subscription')],
            },
        ),
        migrations.RunPython(subscribe_existing_authors, migrations.RunPython.noop),
    ]
