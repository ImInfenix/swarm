import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_apitoken'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='priority',
            field=models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')], default='normal', max_length=10),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('in_progress', 'In progress'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='open', max_length=20),
        ),
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(choices=[('en', 'English'), ('fr', 'Français')], default='en', max_length=2)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
