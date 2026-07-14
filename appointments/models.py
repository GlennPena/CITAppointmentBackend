from django.utils import timezone
from django.db import models
from users.models import User


class Appointment(models.Model):
    """ Stores appointment details between a student and a faculty member """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Expired', 'Expired'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_appointments', null=True, blank=True)
    faculty = models.ForeignKey(User, on_delete=models.CASCADE, related_name='faculty_appointments')
    participants = models.ManyToManyField(User, related_name='participating_appointments', blank=True)

    service = models.CharField(max_length=100, default='General Consultation')

    condition = models.TextField()
    date_time = models.DateTimeField()

    outcome = models.CharField(max_length=255, null=True, blank=True, default="No outcome provided.")
    consultation_notes = models.TextField(null=True, blank=True, default="No specific notes provided.")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    last_status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):

        # Tracks previous status when an update occurs
        if self.pk:
            try:
                old_instance = Appointment.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.last_status = old_instance.status
            except Appointment.DoesNotExist:
                pass

        super().save(*args, **kwargs)