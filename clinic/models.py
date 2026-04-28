from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Clinician(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='clinicians'
    )

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class Patient(models.Model):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    file_number = models.CharField(max_length=50, unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.file_number})"


class AppointmentType(models.Model):
    name = models.CharField(max_length=100)
    duration_minutes = models.IntegerField(default=30)

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE)
    appointment_type = models.ForeignKey(
        AppointmentType,
        on_delete=models.CASCADE
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='booked'
    )

    confirmation_message = models.TextField(blank=True, null=True)
    confirmation_sent = models.BooleanField(default=False)

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Clinical/session notes for this appointment."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def normalise_start_time(self):
        if isinstance(self.start_time, str):
            parsed_start_time = parse_datetime(self.start_time)

            if parsed_start_time is None:
                raise ValidationError("Invalid appointment start time.")

            if timezone.is_naive(parsed_start_time):
                parsed_start_time = timezone.make_aware(parsed_start_time)

            self.start_time = parsed_start_time

    def calculate_end_time(self):
        if self.start_time and self.appointment_type_id:
            self.end_time = self.start_time + timedelta(
                minutes=self.appointment_type.duration_minutes
            )

    def clean(self):
        if not self.start_time:
            return

        self.normalise_start_time()
        self.calculate_end_time()

        if not self.end_time:
            return

        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

        start = self.start_time.time()
        end = self.end_time.time()

        if start < time(8, 0) or end > time(16, 0):
            raise ValidationError(
                "Appointments must be between 08:00 and 16:00."
            )

        if not self.clinician_id:
            return

        overlapping = Appointment.objects.filter(
            clinician_id=self.clinician_id,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
            status='booked'
        ).exclude(id=self.id)

        if overlapping.exists():
            raise ValidationError(
                "This clinician already has a booking in this time slot."
            )

    def generate_confirmation_message(self):
        appointment_date = self.start_time.strftime("%d %B %Y")
        appointment_time = self.start_time.strftime("%H:%M")

        return (
            f"Good day {self.patient.full_name},\n\n"
            f"Your booking has been confirmed at Martha Griffiths CHC.\n\n"
            f"File number: {self.patient.file_number}\n"
            f"Clinician: {self.clinician.name}\n"
            f"Department: {self.clinician.department.name}\n"
            f"Date: {appointment_date}\n"
            f"Time: {appointment_time}\n\n"
            f"Please arrive 10 minutes early.\n\n"
            f"Kind regards,\n"
            f"Martha Griffiths CHC"
        )

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        self.clean()

        if (
            self.patient_id
            and self.clinician_id
            and self.appointment_type_id
            and self.start_time
            and not self.confirmation_message
        ):
            self.confirmation_message = self.generate_confirmation_message()

        super().save(*args, **kwargs)

        if (
            is_new
            and self.patient.email
            and self.confirmation_message
            and not self.confirmation_sent
        ):
            send_mail(
                subject="Appointment Confirmation",
                message=self.confirmation_message,
                from_email=None,
                recipient_list=[self.patient.email],
                fail_silently=True,
            )

            self.confirmation_sent = True
            super().save(update_fields=['confirmation_sent'])

    def __str__(self):
        return (
            f"{self.patient.full_name} - "
            f"{self.clinician.name} - "
            f"{self.start_time}"
        )


class Reminder(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    reminder_time = models.DateTimeField()
    sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder for {self.appointment}"


class Referral(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)

    referred_from = models.ForeignKey(
        Clinician,
        on_delete=models.CASCADE,
        related_name='referrals_made'
    )

    referred_to_department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='referrals_received'
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.patient.full_name} referred to "
            f"{self.referred_to_department.name}"
        )