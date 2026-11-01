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

---

## Етап 2 — рефакторинг: окрема таблиця `air_quality` (`stage2-air-quality-table`)

Міграція `0002_extract_air_quality_table.py` виконує класичну схему **expand → migrate → contract**:

1. **expand** — `CREATE TABLE air_quality` (`id`, `observation_id` FK → `weather_observations.id`
   `ON DELETE CASCADE`, унікальний, + 8 колонок стану повітря);
2. **migrate** — один переносимий запит
   `INSERT INTO air_quality (...) SELECT id, air_quality_* FROM weather_observations`;
3. **contract** — `DROP COLUMN` для 8 старих колонок (через `op.batch_alter_table`, щоб один код
   працював і там, де `ALTER TABLE` обмежений).

`downgrade()` робить зворотне: повертає колонки як nullable → корельований `UPDATE ... (SELECT ... FROM air_quality)`
→ `NOT NULL` → `DROP TABLE air_quality`.

### Перевірка, що дані не втрачено

Контрольні суми по 107 963 рядках до і після міграції (та після `downgrade 0001` → `upgrade head`):

| | `count(*)` | `sum(pm2_5)` | `sum(us_epa_index)` |
|---|---|---|---|
| до 0002 (`weather_observations.air_quality_*`) | 107 963 | 2 727 183.24 | 186 823 |
| після 0002 (`air_quality` JOIN) | 107 963 | 2 727 183.24 | 186 823 |
| після `downgrade 0001` | 107 963 | 2 727 183.24 | 186 823 (NULL-ів: 0) |

`upgrade` ≈ 1.6 с, `downgrade` ≈ 30 с (корельовані `UPDATE` по 8 колонках — повільніше, ніж `INSERT … SELECT`).

### Зміни в коді

- `models.py`: новий клас `AirQuality`, зв'язок 1:1 `WeatherObservation.air_quality` (`relationship`, `cascade="all, delete-orphan"`).
- `import_service.py`: один рядок CSV → два ORM-об'єкти; вставка через `session.add_all()` + `flush()`,
  щоб SQLAlchemy сам проставив `observation_id` (ідентифікатори повертаються через `INSERT … RETURNING`
  у Postgres або `lastrowid` у MySQL — код однаковий).
- `repositories.py`: `AirQualityRepository`, `selectinload` для завантаження зв'язку одним додатковим запитом.
- Імпорт на чисту базу з новою схемою перевірено окремо (`weather_test`, 8 555 рядків → 8 555 + 8 555), ідемпотентність збережена.

Стан бази: `alembic_version = 0002`, таблиці `weather_observations` (12 колонок) + `air_quality` (10 колонок) —
`docs/schema_stage2_postgres.sql`.

---

## Етап 3 — колонка «Чи варто виходити на вулицю» (`stage3-go-outside-flag`)

### Формула (варіант 2 — стан повітря)

```
варто виходити  ⇔  us_epa_index ≤ 2  І  pm2_5 < 35.4 мкг/м³
```

- `us_epa_index`: 1 Good, 2 Moderate, 3 Unhealthy for sensitive groups, 4 Unhealthy, 5 Very Unhealthy, 6 Hazardous —
  з рівня 3 EPA радить обмежити перебування на вулиці;
- `35.4 мкг/м³` — верхня межа категорії «Moderate» для PM2.5 у шкалі EPA AQI. Друга умова страхує від
  випадків, коли сумарний індекс ще 2, а саме дрібний пил уже високий (таких рядків у датасеті 3 305).

Формула живе в **одному місці** — `weather/domain/rules.py` (`is_safe_to_go_outside(reading)`),
чиста функція без залежності від БД, + `explain()` для консольного пояснення.

### Де що

| Шар | Файл | Роль |
|---|---|---|
| міграція | `alembic/versions/0003_add_is_safe_to_go_outside.py` | лише `ADD COLUMN is_safe_to_go_outside BOOLEAN NULL` (+ COMMENT) |
| domain | `weather/domain/rules.py` | формула |
| data | `models.py` → `AirQuality.is_safe_to_go_outside`, `as_reading()`; `repositories.py` → `iter_unfilled()`, `bulk_set_flag()` | зберігання/масове оновлення |
| services | `weather/services/air_quality_service.py` | **заповнення** колонки для існуючих рядків: читає NULL-рядки пачками по 10 000, застосовує правило, масовий `UPDATE … WHERE id = :id` (executemany) |
| services | `import_service.py` | нові рядки отримують відповідь одразу при імпорті |
| presentation | `cli.py fill-go-outside [--all]` | команда запуску |

### Значення за замовчуванням

Колонка створена **без** `DEFAULT` і nullable: `NULL` означає «відповідь ще не обчислено».
Це свідомо: `DEFAULT false` зробив би всі старі рядки «не виходити» і їх не можна було б відрізнити
від справді поганого повітря; `DEFAULT true` — навпаки, приховав би небезпечні випадки.
Після `fill-go-outside` NULL-ів не лишається (перевірено нижче), а нові рядки заповнює імпорт.

### Результат на повному датасеті

```
$ alembic upgrade head           # 0002 -> 0003, ~0.1 с
$ python -m weather.presentation.cli fill-go-outside
Оновлено: 107963 (варто виходити: 87443, не варто: 20520)      # ~15 с
```

Незалежна перевірка чистим SQL: `count(*) filter (where (us_epa_index<=2 and pm2_5<35.4) <> is_safe_to_go_outside)` = **0**,
NULL-ів = **0**. Повторний запуск оновлює 0 рядків (ідемпотентно); `--all` перераховує все заново.

| `us_epa_index` | варто (`true`) | не варто (`false`) |
|---|---|---|
| 1 | 56 359 | 0 |
| 2 | 31 084 | 3 305 (PM2.5 ≥ 35.4) |
| 3–6 | 0 | 17 215 |

Стан бази: `alembic_version = 0003`, `air_quality` + колонка `is_safe_to_go_outside` — `docs/schema_stage3_postgres.sql`.
