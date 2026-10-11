"""Корневая маршрутизация проекта."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(request):
    """Проверка живости приложения для оркестратора/мониторинга."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include("sales.urls")),
    path("health/", health, name="health"),
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]
