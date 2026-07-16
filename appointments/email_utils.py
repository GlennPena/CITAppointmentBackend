from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def send_appointment_email(appointment, action):
    """
    Sends an email notification based on the appointment action.
    """
    if action == "Booked":
        subject = "New Appointment Request"
        # Notify the faculty that a student booked an appointment
        recipient_email = appointment.faculty.email
        formatted_date = timezone.localtime(appointment.date_time).strftime('%B %d, %Y at %I:%M %p')
        message = (
            f"Hello {appointment.faculty.first_name},\n\n"
            f"A new appointment request has been made by {appointment.student.first_name} {appointment.student.last_name}.\n\n"
            f"Details:\n"
            f"Service: {appointment.service}\n"
            f"Date & Time: {formatted_date}\n"
            f"Notes/Condition: {appointment.condition or 'None provided'}\n\n"
            f"Please log in to the CIT Appointment system to approve or reject this request.\n\n"
            f"Best regards,\nCIT Appointment System"
        )
    elif action == "Approved":
        subject = "Appointment Approved"
        # Notify the student
        recipient_email = appointment.student.email
        formatted_date = timezone.localtime(appointment.date_time).strftime('%B %d, %Y at %I:%M %p')
        message = (
            f"Hello {appointment.student.first_name},\n\n"
            f"Your appointment request with {appointment.faculty.first_name} {appointment.faculty.last_name} has been APPROVED.\n\n"
            f"Details:\n"
            f"Service: {appointment.service}\n"
            f"Date & Time: {formatted_date}\n\n"
            f"Please be on time for your appointment.\n\n"
            f"Best regards,\nCIT Appointment System"
        )
    elif action == "Rejected":
        subject = "Appointment Rejected"
        # Notify the student
        recipient_email = appointment.student.email
        formatted_date = timezone.localtime(appointment.date_time).strftime('%B %d, %Y at %I:%M %p')
        message = (
            f"Hello {appointment.student.first_name},\n\n"
            f"We regret to inform you that your appointment request with {appointment.faculty.first_name} {appointment.faculty.last_name} has been REJECTED.\n\n"
            f"Details:\n"
            f"Service: {appointment.service}\n"
            f"Requested Date & Time: {formatted_date}\n\n"
            f"Please log in to the CIT Appointment system to view any messages from the faculty or to book another time slot.\n\n"
            f"Best regards,\nCIT Appointment System"
        )
    else:
        print(f"Unknown email action: {action}")
        return

    if recipient_email:
        try:
            print(f"Attempting to send '{action}' email to {recipient_email}...")
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            print(f"Successfully sent '{action}' email to {recipient_email}")
        except Exception as e:
            print(f"FAILED to send '{action}' email to {recipient_email}: {e}")
    else:
        print(f"No recipient email found for action {action}")
