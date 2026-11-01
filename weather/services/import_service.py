"""Імпорт датасету Global Weather Repository (CSV) у базу даних.

Читаємо ВЕСЬ CSV (41 колонка), але у БД записуємо лише ті колонки, що описані
в ORM-моделях. Повторний запуск не створює дублікатів: рядки, чиї натуральні ключі
(country, location_name, last_updated) вже є в базі, пропускаються.

З етапу 2 один рядок CSV розкладається на два ORM-об'єкти:
WeatherObservation (загальна погода) + AirQuality (стан повітря, 1:1).
З етапу 3 для кожного AirQuality одразу обчислюється is_safe_to_go_outside.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from weather.data.database import session_scope
from weather.data.models import AirQuality, WeatherObservation
from weather.data.repositories import WeatherObservationRepository
from weather.domain.enums import WindDirection
from weather.domain.rules import is_safe_to_go_outside

# колонки CSV -> атрибути WeatherObservation
OBSERVATION_COLUMNS: dict[str, str] = {
    "country": "country",
    "location_name": "location_name",
    "last_updated": "last_updated",
    "temperature_celsius": "temperature_celsius",
    "condition_text": "condition_text",
    "humidity": "humidity",
    "wind_kph": "wind_kph",
    "wind_degree": "wind_degree",
    "wind_direction": "wind_direction",
    "sunrise": "sunrise",
    "sunset": "sunset",
}

# колонки CSV -> атрибути AirQuality
AIR_QUALITY_COLUMNS: dict[str, str] = {
    "air_quality_Carbon_Monoxide": "carbon_monoxide",
    "air_quality_Ozone": "ozone",
    "air_quality_Nitrogen_dioxide": "nitrogen_dioxide",
    "air_quality_Sulphur_dioxide": "sulphur_dioxide",
    "air_quality_PM2.5": "pm2_5",
    "air_quality_PM10": "pm10",
    "air_quality_us-epa-index": "us_epa_index",
    "air_quality_gb-defra-index": "gb_defra_index",
}

BATCH_SIZE = 5_000


@dataclass
class ImportReport:
    total_rows: int
    inserted: int
    skipped_existing: int


def _parse_time(value: str):
    """'04:50 AM' -> datetime.time(4, 50). Датасет інколи містить 'No sunrise' тощо."""
    try:
        return datetime.strptime(value.strip(), "%I:%M %p").time()
    except (ValueError, AttributeError):
        return None


def read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    needed = {**OBSERVATION_COLUMNS, **AIR_QUALITY_COLUMNS}
    missing = set(needed) - set(df.columns)
    if missing:
        raise ValueError(f"У CSV бракує колонок: {sorted(missing)}")
    df = df[list(needed)].rename(columns=needed)
    df["last_updated"] = pd.to_datetime(df["last_updated"], format="%Y-%m-%d %H:%M")
    df["sunrise"] = df["sunrise"].map(_parse_time)
    df["sunset"] = df["sunset"].map(_parse_time)
    df["wind_direction"] = df["wind_direction"].map(WindDirection)
    # sunrise/sunset NOT NULL у моделі: рядки без коректного часу відкидаємо
    df = df.dropna(subset=["sunrise", "sunset"])
    return df


def _to_entities(record: dict) -> WeatherObservation:
    obs_kwargs = {attr: record[attr] for attr in OBSERVATION_COLUMNS.values()}
    obs_kwargs["last_updated"] = obs_kwargs["last_updated"].to_pydatetime()
    aq_kwargs = {attr: record[attr] for attr in AIR_QUALITY_COLUMNS.values()}
    # приводимо numpy-типи до чистого Python, щоб драйвери обох БД їх прийняли
    aq_kwargs = {k: (int(v) if k.endswith("_index") else float(v)) for k, v in aq_kwargs.items()}
    obs_kwargs["humidity"] = int(obs_kwargs["humidity"])
    obs_kwargs["wind_degree"] = int(obs_kwargs["wind_degree"])
    obs_kwargs["wind_kph"] = float(obs_kwargs["wind_kph"])
    obs_kwargs["temperature_celsius"] = float(obs_kwargs["temperature_celsius"])
    air_quality = AirQuality(**aq_kwargs)
    # етап 3: відповідь «чи варто виходити» обчислюємо одразу при імпорті
    air_quality.is_safe_to_go_outside = is_safe_to_go_outside(air_quality.as_reading())
    return WeatherObservation(**obs_kwargs, air_quality=air_quality)


class ImportService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def import_csv(self, path: Path, progress=print) -> ImportReport:
        df = read_csv(path)
        total = len(df)
        with session_scope(self.engine) as session:
            repo = WeatherObservationRepository(session)
            existing = repo.existing_keys()
            keys = list(
                zip(df["country"], df["location_name"], df["last_updated"].dt.to_pydatetime())
            )
            new_df = df[[k not in existing for k in keys]]
            records = new_df.to_dict(orient="records")
            inserted = 0
            for start in range(0, len(records), BATCH_SIZE):
                batch = [_to_entities(r) for r in records[start : start + BATCH_SIZE]]
                inserted += repo.add_all(batch)
                session.expunge_all()  # не тримати 100k об'єктів у пам'яті сесії
                progress(f"  вставлено {inserted}/{len(records)}")
        return ImportReport(total_rows=total, inserted=inserted, skipped_existing=total - inserted)
