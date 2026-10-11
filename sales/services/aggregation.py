"""Агрегации продаж: общий код для API, дашборда и xlsx-отчётов."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from django.db.models import Avg, Count, F, QuerySet, Sum
from django.db.models.functions import ExtractMonth, ExtractQuarter, ExtractYear, TruncMonth

from ..models import MacroIndicator

#: Временные разрезы (строятся по ``week_start``).
TIME_GRAINS = {
    "year": lambda: ExtractYear("week_start"),
    "quarter": lambda: ExtractQuarter("week_start"),
    "month": lambda: TruncMonth("week_start"),
    "month_of_year": lambda: ExtractMonth("week_start"),
    "week": lambda: F("week_start"),
}
#: Категориальные разрезы — прямые поля модели.
DIMENSIONS = ("region", "state", "category", "product", "brand", "customer_segment", "sales_channel")
#: Доступные метрики.
METRICS = {
    "count": lambda: Count("id"),
    "sum_quantity": lambda: Sum("quantity"),
    "sum_revenue": lambda: Sum("revenue"),
    "sum_cost": lambda: Sum("cost"),
    "avg_unit_price": lambda: Avg("unit_price"),
    "avg_discount_pct": lambda: Avg("discount_pct"),
    "avg_revenue": lambda: Avg("revenue"),
}
GROUP_CHOICES = tuple(TIME_GRAINS) + DIMENSIONS


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    """Приводит Decimal к float для JSON/Excel."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}


def aggregate(queryset: QuerySet, group_by: Iterable[str] = (), metrics: Iterable[str] = ("count", "sum_revenue"),
              limit: int = 10000) -> list[dict[str, Any]]:
    """Агрегирует отфильтрованный queryset.

    Args:
        queryset: уже отфильтрованные продажи.
        group_by: разрезы из ``GROUP_CHOICES`` (может быть пустым — тогда одна итоговая строка).
        metrics: метрики из ``METRICS``.
        limit: максимум возвращаемых групп.

    Returns:
        Список словарей: ключи разрезов + ключи метрик.
    """
    group_by, metrics = list(group_by), list(metrics)
    unknown = [g for g in group_by if g not in GROUP_CHOICES] + [m for m in metrics if m not in METRICS]
    if unknown:
        raise ValueError(f"Неизвестные параметры: {', '.join(unknown)}")
    metric_exprs = {m: METRICS[m]() for m in metrics}
    if not group_by:
        return [_clean(queryset.order_by().aggregate(**metric_exprs))]
    time_annotations = {g: TIME_GRAINS[g]() for g in group_by if g in TIME_GRAINS}
    qs = (queryset.order_by().annotate(**time_annotations).values(*group_by)
          .annotate(**metric_exprs).order_by(*group_by))
    return [_clean(row) for row in qs[:limit]]


def macro_by_period(grain: str) -> dict[Any, dict[str, float]]:
    """Средние значения макропоказателей по периодам: ``{период: {показатель: значение}}``."""
    qs = (MacroIndicator.objects.order_by().annotate(period=TIME_GRAINS[grain]())
          .values("period", "indicator").annotate(avg=Avg("value")))
    result: dict[Any, dict[str, float]] = defaultdict(dict)
    for row in qs:
        result[row["period"]][row["indicator"]] = round(row["avg"], 4)
    return result


def attach_macro(rows: list[dict[str, Any]], grain: str) -> list[dict[str, Any]]:
    """Добавляет к строкам агрегата поле ``macro`` (средние показатели за период ``grain``)."""
    lookup = macro_by_period(grain)
    for row in rows:
        row["macro"] = lookup.get(row[grain], {})
    return rows


def macro_for_weeks(weeks: Iterable[date]) -> dict[date, dict[str, float]]:
    """Макропоказатели для набора недель: ``{неделя: {показатель: значение}}``."""
    result: dict[date, dict[str, float]] = defaultdict(dict)
    for row in MacroIndicator.objects.filter(week_start__in=set(weeks)):
        result[row.week_start][row.indicator] = row.value
    return result
