from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """Global registry: any authenticated staff member, at any branch, can
    search for and view a patient's record. `registered_branch` just tracks
    where the patient first registered, not who may see them."""

    queryset = Patient.objects.select_related('registered_branch').all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['mrn', 'first_name', 'last_name', 'phone', 'email']
