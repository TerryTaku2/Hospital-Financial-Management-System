from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('branches.urls')),
    path('api/', include('patients.urls')),
    path('api/', include('opd.urls')),
    path('api/', include('ipd.urls')),
    path('api/', include('appointments.urls')),
]
