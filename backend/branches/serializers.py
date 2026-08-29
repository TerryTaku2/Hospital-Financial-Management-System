from rest_framework import serializers

from .models import Bed, Branch, Ward


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code', 'address', 'city', 'phone', 'is_active', 'created_at']


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ['id', 'branch', 'name', 'ward_type']


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = ['id', 'ward', 'label', 'is_occupied']
