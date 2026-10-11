"""Сериализаторы API."""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import MacroIndicator, SalesTransaction
from .services.aggregation import GROUP_CHOICES, METRICS


class SalesTransactionSerializer(serializers.ModelSerializer):
    """Транзакция продажи."""

    class Meta:
        model = SalesTransaction
        fields = "__all__"


class SalesTransactionWithMacroSerializer(SalesTransactionSerializer):
    """Транзакция + макропоказатели той же недели (``?include_macro=true``)."""

    macro = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField(child=serializers.FloatField()))
    def get_macro(self, obj) -> dict:
        """Берёт предварительно загруженные показатели недели из контекста (без N+1 запросов)."""
        return self.context.get("macro_map", {}).get(obj.week_start, {})


class MacroIndicatorSerializer(serializers.ModelSerializer):
    """Значение макропоказателя за неделю."""

    class Meta:
        model = MacroIndicator
        fields = ["id", "week_start", "indicator", "value"]


class AggregateParamsSerializer(serializers.Serializer):
    """Параметры запроса ``/api/sales/aggregate/`` (помимо фильтров продаж)."""

    group_by = serializers.CharField(required=False, allow_blank=True, default="",
                                     help_text="Разрезы через запятую: " + ", ".join(GROUP_CHOICES))
    metrics = serializers.CharField(required=False, default="count,sum_revenue",
                                    help_text="Метрики через запятую: " + ", ".join(METRICS))
    include_macro = serializers.BooleanField(required=False, default=False,
                                             help_text="Добавить средние макропоказатели (при одном временном разрезе year/month/week)")
    limit = serializers.IntegerField(required=False, default=1000, min_value=1, max_value=10000)

    @staticmethod
    def _split(value: str, allowed, name: str) -> list[str]:
        """Разбивает строку по запятым и проверяет допустимость значений."""
        items = [v.strip() for v in value.split(",") if v.strip()]
        bad = [v for v in items if v not in allowed]
        if bad:
            raise serializers.ValidationError(f"Недопустимые значения {name}: {', '.join(bad)}")
        return items

    def validate_group_by(self, value):
        return self._split(value, GROUP_CHOICES, "group_by")

    def validate_metrics(self, value):
        return self._split(value, METRICS, "metrics") or ["count"]
