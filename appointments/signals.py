from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from .email_utils import send_appointment_email

@receiver(post_save, sender=Appointment)
def handle_appointment_save(sender, instance, created, **kwargs):
    if created:
        # It's a new appointment
        send_appointment_email(instance, "Booked")
    else:
        # It's an updated appointment
        # Check if status changed by comparing instance.status and instance.last_status
        if instance.status != instance.last_status:
            if instance.status == 'Approved':
                send_appointment_email(instance, "Approved")
            elif instance.status == 'Rejected':
                send_appointment_email(instance, "Rejected")
