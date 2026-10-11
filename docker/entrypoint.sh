#!/bin/sh
# Подготовка приложения при старте контейнера: миграции, суперпользователь, данные.
set -e

echo "[entrypoint] Применяю миграции..."
python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "[entrypoint] Создаю суперпользователя (если его нет)..."
  python manage.py createsuperuser --noinput \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" 2>/dev/null || echo "[entrypoint] Суперпользователь уже существует."
fi

echo "[entrypoint] Проверяю данные..."
python manage.py bootstrap_data

exec "$@"
