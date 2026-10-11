"""API-представления: список продаж, агрегации, макропоказатели."""
from collections import defaultdict

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .filters import MacroIndicatorFilter, SalesTransactionFilter
from .models import MacroIndicator, SalesTransaction
from .serializers import (AggregateParamsSerializer, MacroIndicatorSerializer, SalesTransactionSerializer,
                          SalesTransactionWithMacroSerializer)
from .services.aggregation import aggregate as aggregate_sales
from .services.aggregation import attach_macro, macro_for_weeks

TRUE_VALUES = {"1", "true", "yes", "on"}


class SalesTransactionViewSet(ReadOnlyModelViewSet):
    """Продажи: фильтрация, поиск, сортировка, пагинация и агрегации.

    ``?include_macro=true`` добавляет к каждой строке макропоказатели недели продажи.
    """

    queryset = SalesTransaction.objects.all()
    serializer_class = SalesTransactionSerializer
    filterset_class = SalesTransactionFilter
    search_fields = ["transaction_id", "product", "brand", "category", "state"]
    ordering_fields = ["week_start", "date", "revenue", "quantity", "unit_price", "category", "region"]

    def _wants_macro(self) -> bool:
        """Нужно ли подмешивать макропоказатели."""
        return self.request.query_params.get("include_macro", "").lower() in TRUE_VALUES

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"} and self._wants_macro():
            return SalesTransactionWithMacroSerializer
        return super().get_serializer_class()

    @extend_schema(parameters=[OpenApiParameter("include_macro", bool, description="Добавить макропоказатели недели")])
    def list(self, request, *args, **kwargs):
        """Список продаж; макропоказатели подгружаются одним запросом на страницу."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        rows = page if page is not None else list(queryset)
        context = self.get_serializer_context()
        if self._wants_macro():
            context["macro_map"] = macro_for_weeks(r.week_start for r in rows)
        serializer = self.get_serializer(rows, many=True, context=context)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @extend_schema(parameters=[AggregateParamsSerializer], responses={200: dict})
    @action(detail=False, methods=["get"])
    def aggregate(self, request):
        """Агрегирует продажи с теми же фильтрами, что и список.

        Пример: ``/api/sales/aggregate/?year=2023&group_by=month,category&metrics=sum_revenue,count``
        """
        params = AggregateParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        queryset = self.filter_queryset(self.get_queryset())
        rows = aggregate_sales(queryset, data["group_by"], data["metrics"], data["limit"])
        grains = [g for g in data["group_by"] if g in {"year", "month", "week"}]
        if data["include_macro"] and len(grains) == 1:
            attach_macro(rows, grains[0])
        return Response({"count": len(rows), "results": rows})


class MacroIndicatorViewSet(ReadOnlyModelViewSet):
    """Недельные макропоказатели (длинный формат) и вспомогательные представления."""

    queryset = MacroIndicator.objects.all()
    serializer_class = MacroIndicatorSerializer
    filterset_class = MacroIndicatorFilter
    ordering_fields = ["week_start", "indicator", "value"]

    @extend_schema(responses={200: list})
    @action(detail=False, methods=["get"])
    def indicators(self, request):
        """Список названий доступных показателей."""
        names = MacroIndicator.objects.order_by().values_list("indicator", flat=True).distinct()
        return Response(sorted(names))

    @extend_schema(responses={200: list})
    @action(detail=False, methods=["get"])
    def weekly(self, request):
        """Показатели в «широком» виде: одна строка на неделю (без пагинации)."""
        queryset = self.filter_queryset(self.get_queryset())
        table = defaultdict(dict)
        for row in queryset:
            table[row.week_start][row.indicator] = row.value
        return Response([{"week_start": week, **values} for week, values in sorted(table.items())])
