import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_comment_is_hidden_ticket_actual_result_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('spam', 'Spam'), ('abuse', 'Abusive content'), ('other', 'Other')], max_length=20)),
                ('details', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='tracker.comment')),
                ('reporter', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='content_reports', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='tracker.ticket')),
            ],
            options={
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('comment__isnull', True), ('ticket__isnull', False)), models.Q(('comment__isnull', False), ('ticket__isnull', True)), _connector='OR'), name='report_exactly_one_target'), models.UniqueConstraint(condition=models.Q(('ticket__isnull', False)), fields=('reporter', 'ticket'), name='unique_ticket_report'), models.UniqueConstraint(condition=models.Q(('comment__isnull', False)), fields=('reporter', 'comment'), name='unique_comment_report')],
            },
        ),
    ]
