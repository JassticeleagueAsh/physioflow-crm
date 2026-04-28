from django.contrib import admin
from .models import (
    Department,
    Clinician,
    Patient,
    AppointmentType,
    Appointment,
    Reminder,
    Referral,
)

admin.site.register(Department)
admin.site.register(Clinician)
admin.site.register(Patient)
admin.site.register(AppointmentType)
admin.site.register(Appointment)
admin.site.register(Reminder)
admin.site.register(Referral)