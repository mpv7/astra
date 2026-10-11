"""Модели данных: транзакции продаж и недельные макроэкономические показатели."""
from django.db import models

from .utils import week_start_of


class SalesTransaction(models.Model):
    """Одна транзакция продажи строительных материалов (факт-таблица).

    Поля, которых нет в сопоставлении колонок датасета, сохраняются в ``extra`` —
    так импорт не теряет данные, даже если схема файла отличается от ожидаемой.
    """

    transaction_id = models.CharField("ID транзакции", max_length=64, blank=True, db_index=True)
    date = models.DateField("Дата")
    week_start = models.DateField("Начало недели", editable=False, db_index=True)
    region = models.CharField("Регион", max_length=64, blank=True, db_index=True)
    state = models.CharField("Штат", max_length=64, blank=True, db_index=True)
    category = models.CharField("Категория", max_length=128, blank=True, db_index=True)
    product = models.CharField("Товар", max_length=255, blank=True)
    brand = models.CharField("Бренд / поставщик", max_length=128, blank=True)
    customer_segment = models.CharField("Сегмент клиента", max_length=64, blank=True)
    sales_channel = models.CharField("Канал продаж", max_length=64, blank=True)
    quantity = models.DecimalField("Количество", max_digits=14, decimal_places=3, null=True, blank=True)
    unit_price = models.DecimalField("Цена за единицу", max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField("Скидка, %", max_digits=6, decimal_places=3, null=True, blank=True)
    revenue = models.DecimalField("Выручка", max_digits=16, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField("Себестоимость", max_digits=16, decimal_places=2, null=True, blank=True)
    extra = models.JSONField("Прочие поля источника", default=dict, blank=True)

    class Meta:
        verbose_name = "транзакция продажи"
        verbose_name_plural = "транзакции продаж"
        ordering = ["-week_start", "id"]
        indexes = [
            models.Index(fields=["category", "week_start"], name="sales_cat_week_idx"),
            models.Index(fields=["region", "week_start"], name="sales_reg_week_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date} · {self.category or '—'} · {self.revenue}"

    def save(self, *args, **kwargs):
        """Автоматически вычисляет ``week_start`` по ``date`` перед сохранением."""
        self.week_start = week_start_of(self.date)
        super().save(*args, **kwargs)


class MacroIndicator(models.Model):
    """Значение одного макропоказателя за неделю (длинный формат: неделя × показатель)."""

    week_start = models.DateField("Начало недели", db_index=True)
    indicator = models.CharField("Показатель", max_length=64, db_index=True)
    value = models.FloatField("Значение")

    class Meta:
        verbose_name = "макропоказатель"
        verbose_name_plural = "макропоказатели"
        ordering = ["week_start", "indicator"]
        constraints = [
            models.UniqueConstraint(fields=["week_start", "indicator"], name="uniq_macro_week_indicator"),
        ]

    def __str__(self) -> str:
        return f"{self.indicator} @ {self.week_start}: {self.value}"
