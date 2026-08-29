from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BranchScopedQuerysetMixin
from .models import OPDVisit
from .serializers import OPDVisitSerializer


class OPDVisitViewSet(BranchScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = OPDVisit.objects.select_related('patient', 'branch', 'doctor').all()
    serializer_class = OPDVisitSerializer
    permission_classes = [IsAuthenticated]
