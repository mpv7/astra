"""Команда: первичное наполнение БД при старте контейнера (идемпотентно)."""
import os
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from sales.models import SalesTransaction


class Command(BaseCommand):
    """Если БД пуста — грузит реальный датасет из DATA_DIR или демо-данные.

    Переменные окружения: ``SALES_FILE``, ``MACRO_FILE``, ``MACRO_SHEET`` (имена относительно
    DATA_DIR) и ``LOAD_DEMO_DATA`` (1/0). Повторный запуск ничего не делает.
    """

    help = "Заполняет пустую БД реальными или демонстрационными данными."

    def handle(self, *args, **opts):
        if SalesTransaction.objects.exists():
            self.stdout.write("БД уже содержит данные — пропускаю.")
            return
        data_dir = Path(settings.DATA_DIR)
        sales_file = os.environ.get("SALES_FILE", "")
        macro_file = os.environ.get("MACRO_FILE", "")
        if sales_file and (data_dir / sales_file).exists():
            call_command("load_sales", str(data_dir / sales_file), sheet=os.environ.get("SALES_SHEET") or None)
            if macro_file and (data_dir / macro_file).exists():
                call_command("load_macro", str(data_dir / macro_file), sheet=os.environ.get("MACRO_SHEET") or None)
        elif os.environ.get("LOAD_DEMO_DATA", "1").lower() in {"1", "true", "yes"}:
            call_command("load_demo", rows=int(os.environ.get("DEMO_ROWS", "30000")))
        else:
            self.stdout.write("Данных для загрузки нет.")
