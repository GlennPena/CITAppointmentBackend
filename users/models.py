from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """ 
        Uses the AbstractUser model to create a custom user with an additional 'role' field.
        AbstractUser includes fields like username, email, first_name, last_name, password. 
    """
    
    # Personal Information
    first_name = models.CharField(max_length=150, null=False, blank=False)
    last_name = models.CharField(max_length=150, null=False, blank=False)
    date_of_birth = models.DateField(null=True, blank=True) 
    sex = models.CharField(
        max_length=10, 
        choices=[('Male', 'Male'), ('Female', 'Female')],
        null=True, 
        blank=True
    )

    # Contact Information
    contact_number = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(unique=True, null=False, blank=False)

    # Academic Information
    course = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=50, null=True, blank=True)
    section = models.CharField(max_length=50, null=True, blank=True)

    # For Faculty
    specialization = models.CharField(max_length=100, null=True, blank=True)

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("faculty", "Faculty"),
        ("dean", "Dean"),
        ("student", "Student"),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student")

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.role}"
    
    def save(self, *args, **kwargs):
        if self.first_name:
            self.first_name = self.first_name.strip().title()
        if self.last_name:
            self.last_name = self.last_name.strip().title()
        if self.course:
            self.course = self.course.strip().upper()
        if self.specialization:
            self.specialization = self.specialization.strip().title()
        if self.sex:
            self.sex = self.sex.strip().title()
        if self.section:
            self.section = self.section.strip().title()
        if self.year:
            self.year = self.year.strip().title()

        if self.address:
            self.address = self.address.strip()
            
        # Ensure email is always lowercase
        if self.email:
            self.email = self.email.strip().lower()

        super().save(*args, **kwargs)