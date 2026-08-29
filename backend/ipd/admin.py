from django.contrib import admin

from .models import Admission


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'bed', 'branch', 'attending_doctor', 'status', 'admission_date')
    list_filter = ('branch', 'status')
    search_fields = ('patient__mrn', 'patient__first_name', 'patient__last_name')
