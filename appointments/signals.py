from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import Appointment
from .email_utils import send_appointment_email, send_meeting_invite_email

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
            elif instance.status == 'Cancelled':
                send_appointment_email(instance, "Cancelled")


@receiver(m2m_changed, sender=Appointment.participants.through)
def handle_participants_changed(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        # Only notify if this is an internal meeting (no student)
        if not instance.student:
            from users.models import User
            added_users = User.objects.filter(pk__in=pk_set)
            emails = [u.email for u in added_users if u.email]
            if emails:
                send_meeting_invite_email(instance, emails)
