from django.contrib.auth.models import AbstractUser
from django.db import models

from branches.models import Branch


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        BRANCH_ADMIN = 'branch_admin', 'Branch Admin'
        DOCTOR = 'doctor', 'Doctor'
        NURSE = 'nurse', 'Nurse'
        RECEPTIONIST = 'receptionist', 'Receptionist'
        PHARMACIST = 'pharmacist', 'Pharmacist'
        LAB_TECH = 'lab_tech', 'Lab Technician'
        ACCOUNTANT = 'accountant', 'Accountant'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTIONIST)
    # Null only for SUPER_ADMIN, who operates across all branches.
    branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, related_name='staff', null=True, blank=True
    )
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'
