"""Команда: загрузка таблицы продаж из CSV/XLSX в БД (Задание 1.0, п.4)."""
import itertools
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sales.importer import iter_records, record_to_sales, resolve_mapping
from sales.models import SalesTransaction


class Command(BaseCommand):
    """Загружает основной датасет продаж пачками через ``bulk_create`` в одной транзакции."""

    help = "Загружает файл продаж (CSV/XLSX) в таблицу SalesTransaction."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Путь к CSV/XLSX с продажами")
        parser.add_argument("--sheet", help="Имя листа (для xlsx)")
        parser.add_argument("--delimiter", default=",", help="Разделитель CSV")
        parser.add_argument("--map", action="append", default=[], metavar="ПОЛЕ=КОЛОНКА",
                            help="Явное сопоставление, напр. --map revenue=total_sales (можно несколько раз)")
        parser.add_argument("--truncate", action="store_true", help="Очистить таблицу перед загрузкой")
        parser.add_argument("--batch-size", type=int, default=5000)
        parser.add_argument("--limit", type=int, default=0, help="Загрузить только первые N строк")

    def handle(self, *args, **opts):
        path = Path(opts["path"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")
        overrides = dict(item.split("=", 1) for item in opts["map"])
        records = iter_records(path, opts["sheet"], opts["delimiter"])
        first = next(records, None)
        if first is None:
            raise CommandError("Файл пуст.")
        mapping = resolve_mapping(first.keys(), overrides)
        if "date" not in mapping:
            raise CommandError(
                "Не найдена колонка с датой. Колонки файла: " + ", ".join(first.keys())
                + ". Укажите её флагом --map date=<колонка>."
            )
        self.stdout.write("Сопоставление: " + ", ".join(f"{k}←{v}" for k, v in mapping.items()))

        started, loaded, skipped, errors, batch = time.time(), 0, 0, [], []
        with transaction.atomic():
            if opts["truncate"]:
                SalesTransaction.objects.all().delete()
            stream = itertools.chain([first], records)
            for index, record in enumerate(stream, 1):
                if opts["limit"] and index > opts["limit"]:
                    break
                try:
                    batch.append(record_to_sales(record, mapping))
                except ValueError as exc:
                    skipped += 1
                    if len(errors) < 10:
                        errors.append(f"строка {index}: {exc}")
                    continue
                if len(batch) >= opts["batch_size"]:
                    SalesTransaction.objects.bulk_create(batch)
                    loaded += len(batch)
                    batch.clear()
            if batch:
                SalesTransaction.objects.bulk_create(batch)
                loaded += len(batch)
        for line in errors:
            self.stderr.write(self.style.WARNING(line))
        self.stdout.write(self.style.SUCCESS(
            f"Загружено {loaded}, пропущено {skipped} за {time.time() - started:.1f} с."))
