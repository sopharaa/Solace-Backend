import uuid
from django.db import migrations, models


def gen_uuid(apps, schema_editor):
    State = apps.get_model('state_app', 'State')
    for row in State.objects.all():
        row.uuid = uuid.uuid4()
        row.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('state_app', '0002_alter_state_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='state',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, null=True),
        ),
        migrations.RunPython(gen_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='state',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
