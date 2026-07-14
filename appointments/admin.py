from django.contrib import admin
from .models import Appointment


class AppointmentAdmin(admin.ModelAdmin):
    # Customizes how appointments are displayed, filtered, and searched in Django admin

    list_display = ('student', 'faculty', 'date_time', 'status')
    list_filter = ('status', 'date_time')
    search_fields = ('student__username', 'faculty__username')

admin.site.register(Appointment, AppointmentAdmin)
