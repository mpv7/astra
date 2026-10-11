"""Команда: загрузка недельных макропоказателей (Задание 1.1)."""
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sales.importer import DATE_ALIASES, iter_records, parse_date, parse_decimal
from sales.models import MacroIndicator
from sales.utils import week_start_of


class Command(BaseCommand):
    """Разворачивает «широкую» таблицу показателей в длинный формат и делает upsert."""

    help = "Загружает недельные макропоказатели (колонка с датой + числовые колонки-показатели)."

    def add_arguments(self, parser):
        parser.add_argument("path", help="CSV/XLSX с макропоказателями")
        parser.add_argument("--sheet", help="Имя листа (для xlsx)")
        parser.add_argument("--delimiter", default=",")
        parser.add_argument("--date-column", help="Явное имя колонки с датой")

    def handle(self, *args, **opts):
        path = Path(opts["path"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")
        records = iter_records(path, opts["sheet"], opts["delimiter"])
        first = next(records, None)
        if first is None:
            raise CommandError("Файл пуст.")
        date_col = opts["date_column"] or next((a for a in DATE_ALIASES if a in first), None)
        if not date_col or date_col not in first:
            raise CommandError("Не найдена колонка с датой. Колонки: " + ", ".join(first.keys()))

        started, rows, skipped_cols = time.time(), {}, set()
        for record in [first, *records]:
            raw = record.get(date_col)
            if raw in (None, ""):
                continue
            week = week_start_of(parse_date(raw))
            for column, value in record.items():
                if column == date_col:
                    continue
                number = parse_decimal(value)
                if number is None:
                    if value not in (None, ""):
                        skipped_cols.add(column)
                    continue
                rows[(week, column)] = float(number)

        objs = [MacroIndicator(week_start=w, indicator=i, value=v) for (w, i), v in rows.items()]
        with transaction.atomic():
            MacroIndicator.objects.bulk_create(
                objs, batch_size=5000, update_conflicts=True,
                unique_fields=["week_start", "indicator"], update_fields=["value"])
        if skipped_cols:
            self.stderr.write(self.style.WARNING("Нечисловые колонки пропущены: " + ", ".join(sorted(skipped_cols))))
        self.stdout.write(self.style.SUCCESS(f"Загружено {len(objs)} значений за {time.time() - started:.1f} с."))
