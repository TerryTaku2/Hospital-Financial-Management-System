from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('mrn', 'first_name', 'last_name', 'gender', 'registered_branch', 'phone')
    search_fields = ('mrn', 'first_name', 'last_name', 'phone', 'email')
    list_filter = ('registered_branch', 'gender')
