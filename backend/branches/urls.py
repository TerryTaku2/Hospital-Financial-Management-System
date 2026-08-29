from rest_framework.routers import DefaultRouter

from .views import BedViewSet, BranchViewSet, WardViewSet

router = DefaultRouter()
router.register('branches', BranchViewSet, basename='branch')
router.register('wards', WardViewSet, basename='ward')
router.register('beds', BedViewSet, basename='bed')

urlpatterns = router.urls
