from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import BranchScopedQuerysetMixin
from .models import Admission
from .serializers import AdmissionSerializer


class AdmissionViewSet(BranchScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Admission.objects.select_related('patient', 'branch', 'bed', 'attending_doctor').all()
    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # branch is derived from the bed's ward, not the mixin default,
        # so it stays correct even for super_admins (who have no branch of
        # their own) and is validated against the requesting staff member's
        # branch for everyone else.
        bed = serializer.validated_data['bed']
        branch = bed.ward.branch
        user = self.request.user
        if user.role != user.Role.SUPER_ADMIN and branch != user.branch:
            raise PermissionDenied('You can only admit patients to beds in your own branch.')

        serializer.save(branch=branch)
        bed.is_occupied = True
        bed.save(update_fields=['is_occupied'])

    @action(detail=True, methods=['post'])
    def discharge(self, request, pk=None):
        admission = self.get_object()
        if admission.status == Admission.Status.DISCHARGED:
            return Response({'detail': 'Patient already discharged.'}, status=400)

        admission.status = Admission.Status.DISCHARGED
        admission.discharge_date = timezone.now()
        admission.discharge_notes = request.data.get('discharge_notes', '')
        admission.save(update_fields=['status', 'discharge_date', 'discharge_notes'])

        admission.bed.is_occupied = False
        admission.bed.save(update_fields=['is_occupied'])

        return Response(AdmissionSerializer(admission).data)
