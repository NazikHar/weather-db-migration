"""Імпорт датасету Global Weather Repository (CSV) у базу даних.

Читаємо ВЕСЬ CSV (41 колонка), але у БД записуємо лише ті колонки, що описані
в ORM-моделі. Повторний запуск не створює дублікатів: рядки, чиї натуральні ключі
(country, location_name, last_updated) вже є в базі, пропускаються.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from weather.data.database import session_scope
from weather.data.repositories import WeatherObservationRepository
from weather.domain.enums import WindDirection

# назва колонки CSV -> назва атрибута ORM
CSV_TO_ORM: dict[str, str] = {
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
    "air_quality_Carbon_Monoxide": "air_quality_carbon_monoxide",
    "air_quality_Ozone": "air_quality_ozone",
    "air_quality_Nitrogen_dioxide": "air_quality_nitrogen_dioxide",
    "air_quality_Sulphur_dioxide": "air_quality_sulphur_dioxide",
    "air_quality_PM2.5": "air_quality_pm2_5",
    "air_quality_PM10": "air_quality_pm10",
    "air_quality_us-epa-index": "air_quality_us_epa_index",
    "air_quality_gb-defra-index": "air_quality_gb_defra_index",
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
    missing = set(CSV_TO_ORM) - set(df.columns)
    if missing:
        raise ValueError(f"У CSV бракує колонок: {sorted(missing)}")
    df = df[list(CSV_TO_ORM)].rename(columns=CSV_TO_ORM)
    df["last_updated"] = pd.to_datetime(df["last_updated"], format="%Y-%m-%d %H:%M")
    df["sunrise"] = df["sunrise"].map(_parse_time)
    df["sunset"] = df["sunset"].map(_parse_time)
    df["wind_direction"] = df["wind_direction"].map(WindDirection)
    # sunrise/sunset NOT NULL у моделі: рядки без коректного часу відкидаємо
    df = df.dropna(subset=["sunrise", "sunset"])
    return df


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
            mask = [k not in existing for k in keys]
            new_df = df[mask]
            inserted = 0
            records = new_df.to_dict(orient="records")
            for start in range(0, len(records), BATCH_SIZE):
                batch = records[start : start + BATCH_SIZE]
                for r in batch:
                    r["last_updated"] = r["last_updated"].to_pydatetime()
                inserted += repo.bulk_insert(batch)
                progress(f"  вставлено {inserted}/{len(records)}")
        return ImportReport(total_rows=total, inserted=inserted, skipped_existing=total - inserted)
