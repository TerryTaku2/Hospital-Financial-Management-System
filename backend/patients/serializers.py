from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'mrn', 'first_name', 'last_name', 'date_of_birth', 'gender',
            'blood_group', 'phone', 'email', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'registered_branch', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'mrn', 'created_at', 'updated_at']
