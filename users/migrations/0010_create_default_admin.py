from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    if not User.objects.filter(username='admin').exists():
        admin_user = User(
            username='admin',
            email='uacitappointment@gmail.com',
            first_name='System',
            last_name='Admin',
            role='admin',
            is_superuser=True,
            is_staff=True,
            is_active=True,
            password=make_password('admin123')
        )
        admin_user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_passwordresetotp'),
    ]

    operations = [
        migrations.RunPython(create_default_admin),
    ]
