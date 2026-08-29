from django.contrib import admin

from .models import OPDVisit


@admin.register(OPDVisit)
class OPDVisitAdmin(admin.ModelAdmin):
    list_display = ('patient', 'branch', 'doctor', 'visit_date', 'status')
    list_filter = ('branch', 'status', 'doctor')
    search_fields = ('patient__mrn', 'patient__first_name', 'patient__last_name')
