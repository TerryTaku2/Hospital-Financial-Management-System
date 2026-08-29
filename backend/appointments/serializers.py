from rest_framework import serializers

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'branch', 'doctor', 'doctor_name',
            'scheduled_time', 'reason', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'branch', 'created_at']

    def get_patient_name(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username
