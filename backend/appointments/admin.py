from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'branch', 'scheduled_time', 'status')
    list_filter = ('branch', 'status', 'doctor')
    search_fields = ('patient__mrn', 'patient__first_name', 'patient__last_name')
