from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class HospitalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital info', {'fields': ('role', 'branch', 'phone')}),
    )
    list_display = ('username', 'email', 'role', 'branch', 'is_active')
    list_filter = ('role', 'branch', 'is_active')
