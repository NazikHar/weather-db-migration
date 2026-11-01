# Лабораторна 3. Міграція бази даних — варіант 2 (стан повітря)

Програма у стилі **Layered Architecture** на Python: ORM-модель погодної БД
(датасет [Global Weather Repository](https://www.kaggle.com/datasets/nelgiriyewithana/global-weather-repository)),
завантаження з CSV, рефакторинг-міграції через **Alembic**, консольний запит
та перенесення **PostgreSQL → MySQL** тими самими міграціями.

| | |
|---|---|
| Мова | Python 3.11+ |
| ORM | SQLAlchemy 2.x |
| Інструмент міграцій | Alembic |
| БД | PostgreSQL 16 → MySQL / MariaDB 10.11 |
| Категорія варіанта | 2 — **стан повітря** (`air_quality_*`, 8 колонок) |

## Гілки = етапи

| Гілка | Що зроблено | Стан бази після етапу |
|---|---|---|
| `stage1-orm-load` | ORM-модель, міграція `0001`, імпорт CSV | одна плоска таблиця `weather_observations` |
| `stage2-air-quality-table` | рефакторинг: стан повітря винесено в `air_quality` | 2 таблиці, дані збережені |
| `stage3-go-outside-flag` | булева колонка `is_safe_to_go_outside` + її заповнення | `air_quality` + прапорець |
| `stage4-query-cli` | консольний запит: країна + дата (+ місто) | без змін схеми |
| `stage5-migrate-to-mysql` | ті самі міграції накочено на MySQL, дані перенесено, бази звірено | 2 однакові бази |
| `main` | фінальний стан + ця записка | |

Кожна гілка містить `docs/schema_stageN_*.sql` — знімок схеми бази (`pg_dump --schema-only`)
на момент завершення етапу.

## Архітектура (шари)

```
weather/
├── presentation/cli.py        ← консольний інтерфейс (argparse)
├── services/                  ← прикладна логіка: import_service.py, …
├── domain/                    ← предметна область: enums.py (WindDirection), …
├── data/                      ← доступ до даних
│   ├── models.py              ← ORM-моделі SQLAlchemy
│   ├── repositories.py        ← SQL-запити
│   └── database.py            ← engine / session
└── config.py                  ← DATABASE_URL зі змінних оточення
alembic/versions/              ← міграції 0001, 0002, …
data/sample_weather.csv        ← вибірка датасету (8 555 рядків: уся Україна + 8 000 випадкових)
```

Правило шарів: `presentation → services → domain/data`; `domain` не знає про БД.

## Запуск

```bash
pip install -r requirements.txt
cp .env.example .env            # або export DATABASE_URL=...

# PostgreSQL: створити користувача й базу
sudo -u postgres psql -c "CREATE USER weather WITH PASSWORD 'weather';"
sudo -u postgres psql -c "CREATE DATABASE weather_pg OWNER weather;"

alembic upgrade head                          # створити схему з нуля (або домігрувати існуючу)
python -m weather.presentation.cli import     # завантажити data/GlobalWeatherRepository.csv або sample
python -m weather.presentation.cli stats
```

### Дані

Повний датасет (`data/GlobalWeatherRepository.csv`, 28 МБ, 107 963 рядки) у репозиторій не
комітиться (`.gitignore`); завантажте його з Kaggle у `data/`. Без нього `import` бере
`data/sample_weather.csv`. Усі результати нижче отримані на **повному** датасеті.

---

## Етап 1 — ORM-модель та завантаження (`stage1-orm-load`)

### Відібрані колонки

| Вимога | Колонка CSV | Колонка в ORM | Тип SQLAlchemy |
|---|---|---|---|
| текстова | `country` | `country` | `String(100)` |
| ціле | `wind_degree` | `wind_degree` | `Integer` |
| дробове | `wind_kph` | `wind_kph` | `Float` |
| enumeration | `wind_direction` | `wind_direction` | `Enum(WindDirection)` — 16 румбів |
| дата | `last_updated` | `last_updated` | `DateTime` |
| час | `sunrise` | `sunrise` | `Time` |
| категорія 2 | `air_quality_Carbon_Monoxide` | `air_quality_carbon_monoxide` | `Float` |
| | `air_quality_Ozone` | `air_quality_ozone` | `Float` |
| | `air_quality_Nitrogen_dioxide` | `air_quality_nitrogen_dioxide` | `Float` |
| | `air_quality_Sulphur_dioxide` | `air_quality_sulphur_dioxide` | `Float` |
| | `air_quality_PM2.5` | `air_quality_pm2_5` | `Float` |
| | `air_quality_PM10` | `air_quality_pm10` | `Float` |
| | `air_quality_us-epa-index` | `air_quality_us_epa_index` | `Integer` |
| | `air_quality_gb-defra-index` | `air_quality_gb_defra_index` | `Integer` |
| додатково | `location_name`, `temperature_celsius`, `condition_text`, `humidity`, `sunset` | | |

Назви колонок нормалізовано (`PM2.5` → `pm2_5`, `us-epa-index` → `us_epa_index`), бо крапка й дефіс
в ідентифікаторах вимагали б лапок у кожному SQL-запиті та по-різному цитуються у Postgres (`"..."`)
і MySQL (`` `...` ``).

### Особливості

- Унікальний ключ `(country, location_name, last_updated)` робить імпорт **ідемпотентним**:
  повторний запуск вставляє 0 рядків (перевірено: `вставлено: 0, пропущено: 107963`).
- `sunrise`/`sunset` у CSV у форматі `04:50 AM` → парсяться у `datetime.time`.
- `wind_direction` зберігається як **нативний ENUM** (тип `wind_direction` у Postgres,
  `ENUM(...)` у MySQL). У `downgrade()` тип видаляється явно, бо `drop_table` цього не робить.
- Імпорт — масовий (`INSERT` пачками по 5 000 словників, без створення ORM-об'єктів):
  107 963 рядки ≈ 14 с.

Стан бази: `alembic_version = 0001`, таблиця `weather_observations` (20 колонок) —
`docs/schema_stage1_postgres.sql`.
