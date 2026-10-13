from django.conf import settings
from django.db import migrations, models


def classify_legacy_tickets(apps, schema_editor):
    ticket_model = apps.get_model("tracker", "Ticket")
    ticket_model.objects.using(schema_editor.connection.alias).exclude(type__in=["bug", "feature"]).update(type="feature")


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_contentreport'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(classify_legacy_tickets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ticket',
            name='type',
            field=models.CharField(choices=[('bug', 'Bug report'), ('feature', 'Feature request')], max_length=20),
        ),
        migrations.AddConstraint(
            model_name='ticket',
            constraint=models.CheckConstraint(condition=models.Q(('type__in', ['bug', 'feature'])), name='valid_ticket_type'),
        ),
    ]
