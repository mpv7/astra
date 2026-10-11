# Образ приложения Astra Procurement (Django + gunicorn).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока requirements.txt не менялся.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Статика собирается на этапе сборки образа (SQLite-заглушка: БД для collectstatic не нужна).
RUN DB_ENGINE=sqlite DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && chmod +x docker/entrypoint.sh \
    && useradd --create-home --uid 1000 app \
    && chown -R app:app /app

USER app
EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
