from django.conf import settings
from django.db import models

from branches.models import Branch
from patients.models import Patient


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='appointments')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='appointments')
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='appointments',
        limit_choices_to={'role': 'doctor'},
    )
    scheduled_time = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_time']

    def __str__(self):
        return f'{self.patient.mrn} with {self.doctor} @ {self.scheduled_time:%Y-%m-%d %H:%M}'
