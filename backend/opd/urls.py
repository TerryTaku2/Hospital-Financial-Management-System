from rest_framework.routers import DefaultRouter

from .views import OPDVisitViewSet

router = DefaultRouter()
router.register('opd-visits', OPDVisitViewSet, basename='opdvisit')

urlpatterns = router.urls
