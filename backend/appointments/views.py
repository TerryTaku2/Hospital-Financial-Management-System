from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BranchScopedQuerysetMixin
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(BranchScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('patient', 'branch', 'doctor').all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
