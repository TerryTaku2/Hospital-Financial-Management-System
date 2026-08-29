from django.contrib import admin

from .models import Bed, Branch, Ward


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'ward_type')
    list_filter = ('branch', 'ward_type')


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('label', 'ward', 'is_occupied')
    list_filter = ('ward__branch', 'is_occupied')
