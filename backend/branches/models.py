from django.db import models


class Branch(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True, help_text="Short unique code, e.g. 'HQ', 'BR-EAST'")
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class Ward(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='wards')
    name = models.CharField(max_length=100)
    ward_type = models.CharField(
        max_length=30,
        choices=[
            ('general', 'General'),
            ('icu', 'ICU'),
            ('maternity', 'Maternity'),
            ('pediatric', 'Pediatric'),
            ('emergency', 'Emergency'),
            ('surgical', 'Surgical'),
        ],
        default='general',
    )

    class Meta:
        unique_together = ('branch', 'name')

    def __str__(self):
        return f'{self.branch.code} / {self.name}'


class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    label = models.CharField(max_length=20, help_text="e.g. 'A-12'")
    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ('ward', 'label')

    def __str__(self):
        return f'{self.ward} / Bed {self.label}'
