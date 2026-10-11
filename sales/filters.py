"""Фильтры django-filter для продаж и макропоказателей (общие для API, отчётов и админки)."""
from django_filters import BaseInFilter, CharFilter, DateFilter, FilterSet, NumberFilter

from .models import MacroIndicator, SalesTransaction


class CharInFilter(BaseInFilter, CharFilter):
    """Фильтр «значение входит в список» (значения через запятую)."""


class SalesTransactionFilter(FilterSet):
    """Фильтры продаж. Списочные поля принимают несколько значений: ``?region=West,South``."""

    date_from = DateFilter(field_name="week_start", lookup_expr="gte", help_text="Неделя не раньше (YYYY-MM-DD)")
    date_to = DateFilter(field_name="week_start", lookup_expr="lte", help_text="Неделя не позже (YYYY-MM-DD)")
    year = NumberFilter(field_name="week_start", lookup_expr="year")
    month = NumberFilter(field_name="week_start", lookup_expr="month")
    region = CharInFilter(field_name="region", lookup_expr="in")
    state = CharInFilter(field_name="state", lookup_expr="in")
    category = CharInFilter(field_name="category", lookup_expr="in")
    product = CharInFilter(field_name="product", lookup_expr="in")
    brand = CharInFilter(field_name="brand", lookup_expr="in")
    customer_segment = CharInFilter(field_name="customer_segment", lookup_expr="in")
    sales_channel = CharInFilter(field_name="sales_channel", lookup_expr="in")
    quantity_min = NumberFilter(field_name="quantity", lookup_expr="gte")
    quantity_max = NumberFilter(field_name="quantity", lookup_expr="lte")
    revenue_min = NumberFilter(field_name="revenue", lookup_expr="gte")
    revenue_max = NumberFilter(field_name="revenue", lookup_expr="lte")

    class Meta:
        model = SalesTransaction
        fields: list[str] = []


class MacroIndicatorFilter(FilterSet):
    """Фильтры макропоказателей: по названию и периоду."""

    indicator = CharInFilter(field_name="indicator", lookup_expr="in")
    date_from = DateFilter(field_name="week_start", lookup_expr="gte")
    date_to = DateFilter(field_name="week_start", lookup_expr="lte")

    class Meta:
        model = MacroIndicator
        fields: list[str] = []
