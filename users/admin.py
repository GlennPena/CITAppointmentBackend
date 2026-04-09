from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'role', 'course', 'year', 'section', 'is_staff'
    )
    
    list_filter = ('role', 'course', 'year', 'is_staff', 'is_superuser')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Clinic Profile', {
            'fields': (
                'role', 'sex', 'date_of_birth', 'contact_number', 'address'
            )
        }),
        ('Academic Info', {
            'fields': (
                'course', 'year', 'section'
            )
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Personal Details', {
            'fields': (
                'first_name', 'last_name', 'email', 'role', 
                'sex', 'date_of_birth', 'contact_number', 'address',
                'course', 'year', 'section'
            )
        }),
    )

admin.site.register(User, UserAdmin)