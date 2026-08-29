from django.conf import settings
from django.db import models

from branches.models import Branch
from patients.models import Patient


class OPDVisit(models.Model):
    class Status(models.TextChoices):
        WAITING = 'waiting', 'Waiting'
        IN_CONSULTATION = 'in_consultation', 'In Consultation'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='opd_visits')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='opd_visits')
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='opd_visits',
        limit_choices_to={'role': 'doctor'},
    )
    visit_date = models.DateTimeField(auto_now_add=True)
    chief_complaint = models.CharField(max_length=255)
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f'{self.patient.mrn} @ {self.branch.code} - {self.visit_date:%Y-%m-%d}'
