"""Данные для дашборда в админке Unfold (Задание 2.2, п.2)."""
import statistics
from typing import Any

from django.core.cache import cache

from .models import SalesTransaction
from .services.aggregation import aggregate, macro_by_period

CACHE_SECONDS = 300
MONTH_NAMES = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]


def _fmt(value: float | None, suffix: str = "", decimals: int = 0) -> str:
    """Форматирует число с пробелом как разделителем тысяч."""
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}".replace(",", " ") + suffix


def _index(values: list[float]) -> list[float]:
    """Нормирует ряд к 100 по первому значению — чтобы сравнивать разные шкалы."""
    base = values[0] if values and values[0] else 1
    return [round(v / base * 100, 2) for v in values]


def _correlation(xs: list[float], ys: list[float]) -> float | None:
    """Коэффициент Пирсона или None, если ряд вырожден/короткий."""
    try:
        return round(statistics.correlation(xs, ys), 2)
    except (statistics.StatisticsError, ValueError):
        return None


def _share(rows: list[dict[str, Any]], key: str, top: int | None = None) -> dict[str, list]:
    """Готовит labels/values для круговых и столбчатых диаграмм (по убыванию выручки)."""
    rows = sorted(rows, key=lambda r: -(r["sum_revenue"] or 0))[:top]
    return {"labels": [r[key] or "—" for r in rows], "values": [round(r["sum_revenue"] or 0, 2) for r in rows]}


def build_dashboard(year: int | None = None) -> dict[str, Any]:
    """Считает KPI, наборы данных для графиков и корреляции с макропоказателями."""
    qs = SalesTransaction.objects.all()
    if year:
        qs = qs.filter(week_start__year=year)
    totals = aggregate(qs, [], ["count", "sum_quantity", "sum_revenue", "sum_cost", "avg_unit_price", "avg_discount_pct"])[0]
    margin = None
    if totals["sum_revenue"] and totals["sum_cost"]:
        margin = (totals["sum_revenue"] - totals["sum_cost"]) / totals["sum_revenue"] * 100
    kpis = [
        {"title": "Транзакций", "value": _fmt(totals["count"])},
        {"title": "Выручка", "value": _fmt(totals["sum_revenue"], " $")},
        {"title": "Продано единиц", "value": _fmt(totals["sum_quantity"])},
        {"title": "Средняя цена", "value": _fmt(totals["avg_unit_price"], " $", 2)},
        {"title": "Средняя скидка", "value": _fmt(totals["avg_discount_pct"], " %", 1)},
        {"title": "Валовая маржа", "value": _fmt(margin, " %", 1)},
    ]

    yearly = aggregate(SalesTransaction.objects.all(), ["year"], ["sum_revenue"])
    monthly = aggregate(qs, ["month"], ["sum_revenue"])
    seasonal = aggregate(qs, ["month_of_year"], ["sum_revenue"])
    years_count = max(1, len({r["month"].year for r in monthly}))
    charts: dict[str, Any] = {
        "yearly": {"labels": [str(r["year"]) for r in yearly], "values": [round(r["sum_revenue"] or 0, 2) for r in yearly]},
        "monthly": {"labels": [r["month"].strftime("%Y-%m") for r in monthly],
                    "values": [round(r["sum_revenue"] or 0, 2) for r in monthly]},
        "seasonality": {"labels": [MONTH_NAMES[r["month_of_year"] - 1] for r in seasonal],
                        "values": [round((r["sum_revenue"] or 0) / years_count, 2) for r in seasonal]},
        "category": _share(aggregate(qs, ["category"], ["sum_revenue"]), "category", 10),
        "region": _share(aggregate(qs, ["region"], ["sum_revenue"]), "region"),
        "channel": _share(aggregate(qs, ["sales_channel"], ["sum_revenue"]), "sales_channel"),
    }

    macro = macro_by_period("month")
    common = [r for r in monthly if r["month"] in macro]
    indicators = sorted({n for r in common for n in macro[r["month"]]})[:6]
    revenue_series = [r["sum_revenue"] or 0 for r in common]
    datasets, correlations = [], []
    if common:
        datasets.append({"label": "Выручка (индекс)", "data": _index(revenue_series)})
        for name in indicators:
            pairs = [(rev, macro[r["month"]][name]) for rev, r in zip(revenue_series, common) if name in macro[r["month"]]]
            if len(pairs) < 3:
                continue
            values = [p[1] for p in pairs]
            datasets.append({"label": name, "data": _index(values)})
            correlations.append({"indicator": name, "value": _correlation([p[0] for p in pairs], values)})
    charts["macro"] = {"labels": [r["month"].strftime("%Y-%m") for r in common], "datasets": datasets}

    all_years = [r["year"] for r in yearly]
    return {"kpis": kpis, "charts": charts, "correlations": correlations, "years": all_years}


def dashboard_callback(request, context: dict[str, Any]) -> dict[str, Any]:
    """Callback Unfold: добавляет данные дашборда в контекст главной страницы админки."""
    raw = request.GET.get("year", "")
    year = int(raw) if raw.isdigit() else None
    context.update(cache.get_or_set(f"dashboard:{year}", lambda: build_dashboard(year), CACHE_SECONDS))
    context["selected_year"] = year
    return context
