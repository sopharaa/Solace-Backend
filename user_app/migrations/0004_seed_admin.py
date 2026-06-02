from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_admin_user(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    User = apps.get_model('users', 'User')

    admin_role = Role.objects.get(name='ADMIN')

    User.objects.get_or_create(
        email='solace-admin@gmail.com',
        defaults={
            'name': 'Admin',
            'password': make_password('12345solace12345'),
            'role': admin_role,
            'status': 'APPROVED',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        }
    )


def remove_admin_user(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(email='solace-admin@gmail.com').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_seed_roles'),
    ]

    operations = [
        migrations.RunPython(create_admin_user, reverse_code=remove_admin_user),
    ]
