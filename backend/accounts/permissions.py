from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == request.user.Role.SUPER_ADMIN)


class IsBranchAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.role in (user.Role.SUPER_ADMIN, user.Role.BRANCH_ADMIN))


class HasRole(BasePermission):
    """Factory-style permission: HasRole('doctor', 'nurse') restricts to those roles
    (super_admin is always allowed through)."""

    def __init__(self, *roles):
        self.roles = roles

    def __call__(self):
        return self

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.role == user.Role.SUPER_ADMIN or user.role in self.roles


class BranchScopedQuerysetMixin:
    """Restricts a ViewSet's queryset to the requesting user's branch, unless
    they are a super_admin (who sees all branches). Assumes the model has a
    `branch` field, either directly or via `branch_id`."""

    branch_field = 'branch'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == user.Role.SUPER_ADMIN:
            return qs
        return qs.filter(**{self.branch_field: user.branch})

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == user.Role.SUPER_ADMIN:
            # Super admins have no branch of their own, and `branch` is
            # read-only on these serializers, so there is nothing to derive
            # it from here. Operational data entry (OPD visits, admissions,
            # appointments) should happen through a branch-scoped account.
            raise PermissionDenied(
                'Super admins cannot create branch-scoped records directly; '
                'use a branch-scoped staff account instead.'
            )
        serializer.save(**{self.branch_field: user.branch})
