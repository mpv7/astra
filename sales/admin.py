"""Админ-панель на базе django-unfold: таблица продаж, фильтры, поиск, выгрузка отчёта."""
from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import DropdownFilter, RangeDateFilter, RangeNumericFilter
from unfold.decorators import action

from .filters import SalesTransactionFilter
from .models import MacroIndicator, SalesTransaction
from .services.reports import build_summary_workbook

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def distinct_filter(field: str, label: str):
    """Фабрика выпадающего фильтра по уникальным значениям текстового поля (значения кэшируются)."""

    class _Filter(DropdownFilter):
        title = label
        parameter_name = field

        def lookups(self, request, model_admin):
            key = f"distinct:{model_admin.model._meta.label}:{field}"
            values = cache.get_or_set(
                key,
                lambda: list(model_admin.model.objects.order_by().values_list(field, flat=True).distinct()),
                600,
            )
            return [(v, v) for v in sorted(v for v in values if v)]

        def queryset(self, request, queryset):
            value = self.value()
            return queryset.filter(**{field: value}) if value else queryset

    _Filter.__name__ = f"{field.title().replace('_', '')}Filter"
    return _Filter


@admin.register(SalesTransaction)
class SalesTransactionAdmin(ModelAdmin):
    """Таблица продаж с фильтрами, поиском и кнопкой выгрузки сводного отчёта."""

    list_display = ("week_start", "region", "state", "category", "product", "sales_channel",
                    "customer_segment", "quantity", "unit_price", "discount_pct", "revenue")
    list_filter = [
        ("week_start", RangeDateFilter),
        distinct_filter("region", "Регион"),
        distinct_filter("state", "Штат"),
        distinct_filter("category", "Категория"),
        distinct_filter("sales_channel", "Канал продаж"),
        distinct_filter("customer_segment", "Сегмент клиента"),
        ("revenue", RangeNumericFilter),
        ("quantity", RangeNumericFilter),
    ]
    list_filter_submit = True
    search_fields = ("transaction_id", "product", "brand", "category", "state")
    list_per_page = 50
    show_full_result_count = False  # COUNT(*) по сотням тысяч строк на каждый запрос слишком дорог
    ordering = ("-week_start", "id")
    readonly_fields = ("week_start",)
    actions_list = ["export_report"]

    def has_export_report_permission(self, request) -> bool:
        """Выгружать отчёт могут пользователи с правом просмотра продаж."""
        return self.has_view_permission(request)

    @action(description="Выгрузить сводный отчёт (xlsx)", url_path="export-report",
            permissions=["export_report"])
    def export_report(self, request):
        """Отдаёт xlsx-отчёт; понимает те же GET-параметры, что и API (``?year=2023&region=West``)."""
        filterset = SalesTransactionFilter(request.GET, queryset=SalesTransaction.objects.all())
        queryset = filterset.qs if filterset.is_valid() else SalesTransaction.objects.all()
        note = ", ".join(f"{k}={v}" for k, v in request.GET.items())
        response = HttpResponse(build_summary_workbook(queryset, note), content_type=XLSX_MIME)
        stamp = timezone.now().strftime("%Y%m%d_%H%M")
        response["Content-Disposition"] = f'attachment; filename="sales_report_{stamp}.xlsx"'
        return response


@admin.register(MacroIndicator)
class MacroIndicatorAdmin(ModelAdmin):
    """Недельные макропоказатели (только просмотр и фильтрация)."""

    list_display = ("week_start", "indicator", "value")
    list_filter = [("week_start", RangeDateFilter), distinct_filter("indicator", "Показатель")]
    list_filter_submit = True
    search_fields = ("indicator",)
    list_per_page = 100
