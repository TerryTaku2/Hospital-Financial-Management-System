from rest_framework import serializers

from .models import Admission


class AdmissionSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            'id', 'patient', 'patient_name', 'branch', 'bed', 'attending_doctor',
            'reason', 'status', 'admission_date', 'discharge_date', 'discharge_notes',
        ]
        read_only_fields = ['id', 'branch', 'status', 'admission_date', 'discharge_date']

    def get_patient_name(self, obj):
        return f'{obj.patient.first_name} {obj.patient.last_name}'

    def validate_bed(self, bed):
        if bed.is_occupied:
            raise serializers.ValidationError('This bed is already occupied.')
        return bed
