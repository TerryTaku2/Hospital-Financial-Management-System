from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsBranchAdminOrSuperAdmin
from .serializers import HospitalTokenObtainPairSerializer, UserCreateSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = HospitalTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Staff management. Branch admins manage staff within their own branch;
    super admins manage staff across all branches."""

    def get_permissions(self):
        # Any authenticated staff member can list/view colleagues (e.g. to
        # pick a doctor when booking an OPD visit or appointment); only
        # branch/super admins can create, edit, or deactivate accounts.
        if self.action in ('list', 'retrieve', 'me'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsBranchAdminOrSuperAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.select_related('branch').order_by('username')
        if user.role == User.Role.SUPER_ADMIN:
            return qs
        return qs.filter(branch=user.branch)

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == User.Role.SUPER_ADMIN:
            serializer.save()
        else:
            serializer.save(branch=user.branch)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)
