import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_backend.settings')
django.setup()

from users.models import User

def create_admin_account():
    username = input("Enter admin username (default: admin): ").strip() or "admin"
    email = input("Enter admin email (default: admin@ua.edu.ph): ").strip() or "admin@ua.edu.ph"
    password = input("Enter admin password (default: admin123): ").strip() or "admin123"

    if User.objects.filter(username=username).exists():
        print(f"❌ User with username '{username}' already exists.")
        return

    try:
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name="System",
            last_name="Admin",
            role="admin"  # Set custom role directly to admin
        )
        print(f"✅ Admin account '{username}' created successfully with role 'admin'!")
    except Exception as e:
        print(f"❌ Error creating admin account: {e}")

if __name__ == "__main__":
    create_admin_account()
