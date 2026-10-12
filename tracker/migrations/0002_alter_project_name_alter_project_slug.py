import hashlib

import tracker.models
from django.db import migrations, models
from django.utils.text import slugify


def shorten_project_slugs(apps, schema_editor):
    project_model = apps.get_model("tracker", "Project")
    projects = project_model.objects.using(schema_editor.connection.alias)
    used = {slug for slug in projects.values_list("slug", flat=True) if len(slug) <= 10}
    for project in projects.order_by("pk"):
        if len(project.slug) <= 10:
            continue
        base = slugify(project.name)[:10].strip("-") or "p" + hashlib.sha256(project.name.encode("utf-8")).hexdigest()[:9]
        index = 1
        while True:
            suffix = "" if index == 1 else f"-{index}"
            candidate = f"{base[:10 - len(suffix)].rstrip('-')}{suffix}"
            if candidate not in used:
                break
            index += 1
        project.slug = candidate
        project.save(using=schema_editor.connection.alias, update_fields=["slug"])
        used.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(shorten_project_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='project',
            name='name',
            field=models.CharField(max_length=80, validators=[tracker.models.validate_project_name]),
        ),
        migrations.AlterField(
            model_name='project',
            name='slug',
            field=models.SlugField(blank=True, editable=False, max_length=10, unique=True),
        ),
    ]
