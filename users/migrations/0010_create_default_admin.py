from django.db import migrations

def create_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    if not User.objects.filter(username='admin').exists():
        admin_user = User(
            username='admin',
            email='admin@ua.edu.ph',
            first_name='System',
            last_name='Admin',
            role='admin',
            is_superuser=True,
            is_staff=True,
            is_active=True
        )
        admin_user.set_password('admin123')
        admin_user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_passwordresetotp'),
    ]

    operations = [
        migrations.RunPython(create_default_admin),
    ]
