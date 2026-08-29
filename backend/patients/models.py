from django.db import models

from branches.models import Branch


class Patient(models.Model):
    """Global patient registry, shared across all branches so a patient never
    has to re-register when visiting a different location."""

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    # Nullable so concurrent inserts (e.g. two receptionists registering
    # patients at different branches at once) don't collide on '' before the
    # real MRN is assigned post-insert; DBs treat multiple NULLs as distinct
    # under a unique constraint.
    mrn = models.CharField(
        max_length=20, unique=True, null=True, blank=True, editable=False,
        help_text='Medical Record Number',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    blood_group = models.CharField(max_length=5, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)

    registered_branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, related_name='registered_patients'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mrn} - {self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.mrn:
            self.mrn = f'MRN-{self.pk:06d}'
            super().save(update_fields=['mrn'])
