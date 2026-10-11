# Astra Procurement — продажи строительных материалов

Backend-проект отборочного задания мастерской Astra: загрузка датасета
[US Building Materials Sales Transactions 2019–2024](https://www.kaggle.com/datasets/sergionefedov/us-building-materials-sales-transactions-20192024)
в PostgreSQL, REST API на Django, админ-панель на Unfold с графиками и выгрузкой xlsx, Docker.

Обоснование выбора СУБД и архитектуры хранения макропоказателей — в [docs/DECISIONS.md](docs/DECISIONS.md).

## Структура проекта

```
config/                     настройки Django, корневые URL, wsgi/asgi
sales/
  models.py                 SalesTransaction (факты), MacroIndicator (недельные показатели)
  importer.py               чтение CSV/XLSX, сопоставление колонок, разбор значений
  filters.py                FilterSet для API, отчётов и админки
  serializers.py, views.py, urls.py   REST API
  admin.py                  Unfold: таблица, фильтры, поиск, кнопка выгрузки xlsx
  dashboard.py              данные для графиков дашборда (с кэшем)
  services/aggregation.py   общая логика агрегаций (API, дашборд, отчёты)
  services/reports.py       построение xlsx-отчёта (openpyxl)
  management/commands/      inspect_dataset, load_sales, load_macro, load_demo, bootstrap_data
  migrations/, tests.py
templates/admin/index.html  дашборд (Chart.js)
docker/entrypoint.sh        миграции → суперпользователь → загрузка данных → запуск
Dockerfile, docker-compose.yml, .env.example
```

## Быстрый старт (Docker)

```bash
cp .env.example .env            # при желании поменяйте пароли
```

**Режим 1 — сборка образа при запуске:**
```bash
docker compose --profile build up --build
```

**Режим 2 — готовый образ** (из GHCR; укажите свой `APP_IMAGE` в `.env`):
```bash
docker compose --profile image up
```

Откройте: админка и дашборд — http://localhost:8000/admin/ (логин/пароль из `.env`, по умолчанию `admin` / `admin12345`),
документация API — http://localhost:8000/api/docs/.

При первом старте, если БД пуста, загружаются **демо-данные** (30 000 продаж + макропоказатели).

### Загрузка настоящего датасета
1. Скачайте файлы с Kaggle и положите в `./data/` (каталог монтируется в контейнер как `/data`).
2. Посмотрите структуру: `docker compose --profile build run --rm app-build python manage.py inspect_dataset`
3. В `.env` задайте `SALES_FILE=имя_файла.csv`, `MACRO_FILE=...` (для xlsx-листа — `MACRO_SHEET`), `LOAD_DEMO_DATA=0`.
4. Пересоздайте БД: `docker compose down -v && docker compose --profile build up --build`.

Если колонки назвались неожиданно, сопоставьте их вручную (см. ниже) или поправьте `COLUMN_ALIASES` в `sales/importer.py`.

## Локальная разработка

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=1 DB_ENGINE=sqlite        # или поднимите Postgres и задайте POSTGRES_*
python manage.py migrate
python manage.py createsuperuser
python manage.py load_demo                    # или load_sales / load_macro
python manage.py runserver
python manage.py test                         # тесты
```

## Команды загрузки данных

```bash
python manage.py inspect_dataset data/*.csv
python manage.py load_sales data/sales.csv --truncate
python manage.py load_sales data/sales.csv --map revenue=total_sales --map date=week_ending
python manage.py load_macro data/macro.csv            # или --sheet "Macro" для xlsx
python manage.py load_demo --rows 50000 --truncate
```
`load_macro` разворачивает таблицу «колонка с датой + показатели» в длинный формат и делает upsert (повторный запуск безопасен).

## API

| Метод и путь | Описание |
|---|---|
| `GET /api/sales/` | Продажи: фильтры, поиск `?search=`, сортировка `?ordering=-revenue`, пагинация `?page=` |
| `GET /api/sales/?include_macro=true` | То же + поле `macro` (показатели недели продажи) |
| `GET /api/sales/aggregate/` | Агрегации с теми же фильтрами |
| `GET /api/macro/`, `/api/macro/indicators/`, `/api/macro/weekly/` | Макропоказатели: длинный список, названия, «широкая» таблица по неделям |
| `GET /api/docs/`, `/api/schema/` | Swagger UI и OpenAPI-схема |
| `GET /health/` | Проверка живости |

**Фильтры продаж:** `date_from`, `date_to`, `year`, `month`, `region`, `state`, `category`, `product`, `brand`,
`customer_segment`, `sales_channel` (несколько значений через запятую), `quantity_min/max`, `revenue_min/max`.

**Агрегации:** `group_by` — `year, quarter, month, month_of_year, week, region, state, category, product, brand, customer_segment, sales_channel`;
`metrics` — `count, sum_quantity, sum_revenue, sum_cost, avg_unit_price, avg_discount_pct, avg_revenue`; `include_macro=true` — средние показатели за период.

```bash
curl "localhost:8000/api/sales/?region=West,South&year=2023&revenue_min=1000&include_macro=true"
curl "localhost:8000/api/sales/aggregate/?year=2023&group_by=month,category&metrics=sum_revenue,count"
curl "localhost:8000/api/sales/aggregate/?group_by=year&metrics=sum_revenue&include_macro=true"
```

## Админ-панель
- **Дашборд** (главная страница): KPI, выручка по месяцам/годам, сезонность, категории, регионы, каналы,
  сравнение выручки с макропоказателями (индекс) и коэффициенты корреляции. Выбор года сверху.
- **Продажи:** таблица с фильтрами (диапазон дат/выручки/количества, выпадающие списки), поиском и кнопкой
  «Выгрузить сводный отчёт (xlsx)». Отчёт принимает те же параметры, что API: `/admin/sales/salestransaction/export-report/?year=2023&region=West`.

Графики используют Chart.js с CDN (jsDelivr): браузеру нужен доступ в интернет.

## Docstrings и стиль
Docstring-и есть у всех модулей, классов и основных функций. Проверка: `python -m pydoc sales.services.aggregation`.

## Что важно знать
- Схема модели и `COLUMN_ALIASES` составлены без доступа к реальному файлу — сверьте их с `inspect_dataset` и при необходимости измените модель и миграцию (`python manage.py makemigrations`).
- Для продакшена задайте `DJANGO_SECRET_KEY`, сильные пароли, `DJANGO_ALLOWED_HOSTS`; API сейчас открыт на чтение без авторизации.
