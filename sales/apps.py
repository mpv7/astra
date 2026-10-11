"""Конфигурация приложения sales."""
from django.apps import AppConfig


class SalesConfig(AppConfig):
    """Приложение с данными о продажах строительных материалов и макропоказателях."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "sales"
    verbose_name = "Продажи"
