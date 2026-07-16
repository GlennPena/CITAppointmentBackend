from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def send_appointment_email(appointment, action):
    """
    Sends an email notification based on the appointment action.
    """
    recipient_emails = []
    subject = ""
    message = ""

    if action == "Booked":
        # Internal meeting (faculty/dean booking) — no student, notify participants instead
        if not appointment.student:
            print("Internal meeting booked — no student to notify.")
            return

        subject = "New Appointment Request"
        # Notify the faculty that a student booked an appointment
        recipient_emails = [appointment.faculty.email]
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
        # Skip if no student (internal meeting)
        if not appointment.student:
            print("Internal meeting approved — no student to notify.")
            return
        recipient_emails = [appointment.student.email]
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
        # Skip if no student (internal meeting)
        if not appointment.student:
            print("Internal meeting rejected — no student to notify.")
            return
        recipient_emails = [appointment.student.email]
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
    elif action == "Cancelled":
        formatted_date = timezone.localtime(appointment.date_time).strftime('%B %d, %Y at %I:%M %p')
        if appointment.student:
            if appointment.last_status == "Approved":
                # Cancelled by faculty — notify student
                subject = "Appointment Cancelled by Faculty"
                recipient_emails = [appointment.student.email]
                message = (
                    f"Hello {appointment.student.first_name},\n\n"
                    f"We regret to inform you that your scheduled appointment with {appointment.faculty.first_name} {appointment.faculty.last_name} has been CANCELLED by the faculty member.\n\n"
                    f"Details:\n"
                    f"Service: {appointment.service}\n"
                    f"Date & Time: {formatted_date}\n\n"
                    f"Please log in to the CIT Appointment system to reschedule or book another slot.\n\n"
                    f"Best regards,\nCIT Appointment System"
                )
            else:
                # Cancelled by student (last_status was Pending or other) — notify faculty
                subject = "Appointment Cancelled by Student"
                recipient_emails = [appointment.faculty.email]
                message = (
                    f"Hello {appointment.faculty.first_name},\n\n"
                    f"The following appointment request has been cancelled by the student.\n\n"
                    f"Student: {appointment.student.first_name} {appointment.student.last_name}\n"
                    f"Service: {appointment.service}\n"
                    f"Requested Date & Time: {formatted_date}\n\n"
                    f"The time slot is now available for other bookings.\n\n"
                    f"Best regards,\nCIT Appointment System"
                )
        else:
            # Internal meeting cancelled — notify all participants
            participants = list(appointment.participants.all())
            if not participants:
                print("Internal meeting cancelled — no participants to notify.")
                return
            subject = f"Meeting Cancelled: {appointment.service}"
            recipient_emails = [p.email for p in participants if p.email]
            message = (
                f"Hello,\n\n"
                f"Please be informed that the internal meeting scheduled by {appointment.faculty.first_name} {appointment.faculty.last_name} has been CANCELLED.\n\n"
                f"Details:\n"
                f"Meeting: {appointment.service}\n"
                f"Scheduled Date & Time: {formatted_date}\n\n"
                f"Best regards,\nCIT Appointment System"
            )
    else:
        print(f"Unknown email action: {action}")
        return

    # Filter out empty or None emails
    recipient_emails = [email for email in recipient_emails if email]

    if recipient_emails:
        try:
            print(f"Attempting to send '{action}' email to {recipient_emails}...")
            send_mail(
                subject=subject,
                message=message,
                from_email='UACIT Appointment System <uacitappointment@gmail.com>',
                recipient_list=recipient_emails,
                fail_silently=False,
            )
            print(f"Successfully sent '{action}' email to {recipient_emails}")
        except Exception as e:
            print(f"FAILED to send '{action}' email to {recipient_emails}: {e}")
    else:
        print(f"No recipient email found for action {action}")


def send_meeting_invite_email(appointment, participant_emails):
    """
    Sends an email invitation to all designated participants of an internal faculty meeting.
    """
    if not participant_emails:
        return

    formatted_date = timezone.localtime(appointment.date_time).strftime('%B %d, %Y at %I:%M %p')
    subject = f"New Faculty Meeting Invitation: {appointment.service}"
    message = (
        f"Hello,\n\n"
        f"You have been invited to a faculty meeting scheduled by {appointment.faculty.first_name} {appointment.faculty.last_name}.\n\n"
        f"Details:\n"
        f"Meeting: {appointment.service}\n"
        f"Date & Time: {formatted_date}\n"
        f"Notes/Agenda: {appointment.condition or 'No agenda provided'}\n\n"
        f"Please check your schedule and log in to the CIT Appointment system to view details.\n\n"
        f"Best regards,\nCIT Appointment System"
    )

    try:
        print(f"Attempting to send meeting invitation email to {participant_emails}...")
        send_mail(
            subject=subject,
            message=message,
            from_email='UACIT Appointment System <uacitappointment@gmail.com>',
            recipient_list=participant_emails,
            fail_silently=False,
        )
        print(f"Successfully sent meeting invitation email to {participant_emails}")
    except Exception as e:
        print(f"FAILED to send meeting invitation email to {participant_emails}: {e}")
