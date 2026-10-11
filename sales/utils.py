"""Мелкие общие утилиты."""
from datetime import date, timedelta


def week_start_of(value: date) -> date:
    """Возвращает понедельник недели, в которую попадает дата.

    Ключ ``week_start`` связывает таблицу продаж с недельными макропоказателями.
    """
    return value - timedelta(days=value.weekday())
