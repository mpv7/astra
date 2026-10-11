"""Команда: показать структуру файлов датасета (Задание 1.0, п.2 — изучение таблиц)."""
from itertools import islice
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sales.importer import COLUMN_ALIASES, iter_records, list_sheets, resolve_mapping


class Command(BaseCommand):
    """Печатает листы, колонки, примеры строк и результат автосопоставления колонок."""

    help = "Показывает структуру CSV/XLSX-файлов: колонки, примеры, сопоставление с полями модели."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", help="Файлы; по умолчанию все csv/xlsx из DATA_DIR")
        parser.add_argument("--rows", type=int, default=3, help="Сколько строк-примеров показать")

    def handle(self, *args, **opts):
        paths = [Path(p) for p in opts["paths"]] or sorted(
            p for p in Path(settings.DATA_DIR).glob("*") if p.suffix.lower() in {".csv", ".xlsx", ".xlsm"}
        )
        if not paths:
            raise CommandError(f"Файлы не найдены (искали в {settings.DATA_DIR}).")
        for path in paths:
            sheets = list_sheets(path) or [None]
            for sheet in sheets:
                self._describe(path, sheet, opts["rows"])

    def _describe(self, path: Path, sheet: str | None, rows: int) -> None:
        """Описывает один файл (или лист)."""
        title = f"{path.name}" + (f" [лист: {sheet}]" if sheet else "")
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n== {title}"))
        records = iter_records(path, sheet)
        sample = list(islice(records, rows))
        if not sample:
            self.stdout.write("  (пусто)")
            return
        self.stdout.write("Колонки: " + ", ".join(sample[0].keys()))
        for row in sample:
            self.stdout.write("  " + str(row))
        mapping = resolve_mapping(sample[0].keys())
        missing = [f for f in COLUMN_ALIASES if f not in mapping]
        self.stdout.write("Автосопоставление: " + (", ".join(f"{k}←{v}" for k, v in mapping.items()) or "—"))
        if missing:
            self.stdout.write(self.style.WARNING("Не сопоставлены поля модели: " + ", ".join(missing)))
