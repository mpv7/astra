"""Начальная миграция: транзакции продаж и макропоказатели."""
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SalesTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_id", models.CharField(blank=True, db_index=True, max_length=64, verbose_name="ID транзакции")),
                ("date", models.DateField(verbose_name="Дата")),
                ("week_start", models.DateField(db_index=True, editable=False, verbose_name="Начало недели")),
                ("region", models.CharField(blank=True, db_index=True, max_length=64, verbose_name="Регион")),
                ("state", models.CharField(blank=True, db_index=True, max_length=64, verbose_name="Штат")),
                ("category", models.CharField(blank=True, db_index=True, max_length=128, verbose_name="Категория")),
                ("product", models.CharField(blank=True, max_length=255, verbose_name="Товар")),
                ("brand", models.CharField(blank=True, max_length=128, verbose_name="Бренд / поставщик")),
                ("customer_segment", models.CharField(blank=True, max_length=64, verbose_name="Сегмент клиента")),
                ("sales_channel", models.CharField(blank=True, max_length=64, verbose_name="Канал продаж")),
                ("quantity", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True, verbose_name="Количество")),
                ("unit_price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="Цена за единицу")),
                ("discount_pct", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True, verbose_name="Скидка, %")),
                ("revenue", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, verbose_name="Выручка")),
                ("cost", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, verbose_name="Себестоимость")),
                ("extra", models.JSONField(blank=True, default=dict, verbose_name="Прочие поля источника")),
            ],
            options={
                "verbose_name": "транзакция продажи",
                "verbose_name_plural": "транзакции продаж",
                "ordering": ["-week_start", "id"],
            },
        ),
        migrations.CreateModel(
            name="MacroIndicator",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("week_start", models.DateField(db_index=True, verbose_name="Начало недели")),
                ("indicator", models.CharField(db_index=True, max_length=64, verbose_name="Показатель")),
                ("value", models.FloatField(verbose_name="Значение")),
            ],
            options={
                "verbose_name": "макропоказатель",
                "verbose_name_plural": "макропоказатели",
                "ordering": ["week_start", "indicator"],
            },
        ),
        migrations.AddIndex(
            model_name="salestransaction",
            index=models.Index(fields=["category", "week_start"], name="sales_cat_week_idx"),
        ),
        migrations.AddIndex(
            model_name="salestransaction",
            index=models.Index(fields=["region", "week_start"], name="sales_reg_week_idx"),
        ),
        migrations.AddConstraint(
            model_name="macroindicator",
            constraint=models.UniqueConstraint(fields=["week_start", "indicator"], name="uniq_macro_week_indicator"),
        ),
    ]
