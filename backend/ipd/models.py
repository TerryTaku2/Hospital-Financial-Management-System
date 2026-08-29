from django.conf import settings
from django.db import models

from branches.models import Bed, Branch
from patients.models import Patient


class Admission(models.Model):
    class Status(models.TextChoices):
        ADMITTED = 'admitted', 'Admitted'
        DISCHARGED = 'discharged', 'Discharged'

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='admissions')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='admissions')
    attending_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='admissions',
        limit_choices_to={'role': 'doctor'},
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ADMITTED)
    admission_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-admission_date']

    def __str__(self):
        return f'{self.patient.mrn} - {self.bed} ({self.status})'
