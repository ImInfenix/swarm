from django.db import migrations, models


def mark_existing_duplicates(apps, schema_editor):
    Ticket = apps.get_model("tracker", "Ticket")
    Ticket.objects.filter(duplicate_of__isnull=False).update(closure_reason="duplicate")


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0010_ticketattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='closure_reason',
            field=models.CharField(blank=True, choices=[('declined', 'Declined'), ('cannot_reproduce', 'Cannot reproduce'), ('duplicate', 'Duplicate'), ('other', 'Other')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='ticket',
            name='decision_note',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('in_progress', 'In progress'), ('needs_info', 'Needs information'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='open', max_length=20),
        ),
        migrations.RunPython(mark_existing_duplicates, migrations.RunPython.noop),
    ]
