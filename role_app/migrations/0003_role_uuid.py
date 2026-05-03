import uuid
from django.db import migrations, models


def gen_uuid(apps, schema_editor):
    Role = apps.get_model('role_app', 'Role')
    for row in Role.objects.all():
        row.uuid = uuid.uuid4()
        row.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('role_app', '0002_role_permission'),
    ]

    operations = [
        # Step 1: add the field as nullable (no unique yet)
        migrations.AddField(
            model_name='role',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, null=True),
        ),
        # Step 2: populate unique UUIDs for existing rows
        migrations.RunPython(gen_uuid, migrations.RunPython.noop),
        # Step 3: make it non-null + unique
        migrations.AlterField(
            model_name='role',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
