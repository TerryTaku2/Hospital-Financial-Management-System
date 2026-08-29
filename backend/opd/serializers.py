from rest_framework import serializers

from .models import OPDVisit


class OPDVisitSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = OPDVisit
        fields = [
            'id', 'patient', 'patient_name', 'branch', 'doctor', 'doctor_name',
            'visit_date', 'chief_complaint', 'diagnosis', 'notes', 'status',
            'consultation_fee',
        ]
        read_only_fields = ['id', 'branch', 'visit_date']

    def get_patient_name(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username
