from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BranchScopedQuerysetMixin, IsSuperAdmin
from .models import Bed, Branch, Ward
from .serializers import BedSerializer, BranchSerializer, WardSerializer


class BranchViewSet(viewsets.ModelViewSet):
    """Every authenticated user can read the branch list (needed for dropdowns,
    transfers, etc.); only super admins can create/edit/deactivate branches."""

    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSuperAdmin()]


class WardViewSet(BranchScopedQuerysetMixin, viewsets.ModelViewSet):
    """Setting up wards is admin/facilities work, not clinical data entry, so
    (unlike OPD/IPD/appointments) super admins are allowed to create them —
    they just have to specify which branch, since `branch` is writable here."""

    queryset = Ward.objects.select_related('branch').all()
    serializer_class = WardSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == user.Role.SUPER_ADMIN:
            serializer.save()
        else:
            serializer.save(branch=user.branch)


class BedViewSet(viewsets.ModelViewSet):
    """Beds are scoped to the requesting user's branch via their ward."""

    serializer_class = BedSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Bed.objects.select_related('ward', 'ward__branch').all()
        user = self.request.user
        if user.role == user.Role.SUPER_ADMIN:
            return qs
        return qs.filter(ward__branch=user.branch)

    def perform_create(self, serializer):
        ward = serializer.validated_data['ward']
        user = self.request.user
        if user.role != user.Role.SUPER_ADMIN and ward.branch != user.branch:
            raise PermissionDenied('You can only add beds to wards in your own branch.')
        serializer.save()
