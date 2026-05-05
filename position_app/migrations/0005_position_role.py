from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('position_app', '0004_position_uuid_staffposition_uuid'),
        ('role_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='role',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='positions',
                to='role_app.role',
            ),
        ),
    ]
