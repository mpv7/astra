"""Маршруты API приложения sales."""
from rest_framework.routers import DefaultRouter

from .views import MacroIndicatorViewSet, SalesTransactionViewSet

router = DefaultRouter()
router.register("sales", SalesTransactionViewSet, basename="sales")
router.register("macro", MacroIndicatorViewSet, basename="macro")

urlpatterns = router.urls
