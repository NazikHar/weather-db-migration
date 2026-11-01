"""ORM-моделі (SQLAlchemy 2.x, declarative).

Етап 1: одна «плоска» таблиця weather_observations, у якій описано лише
обрані колонки датасету Global Weather Repository (варіант 2 — стан повітря):

    обов'язкові типи      : country (текст), wind_degree (ціле), wind_kph (дробове),
                            wind_direction (enum), last_updated (дата-час), sunrise (час)
    категорія «стан повітря»: air_quality_* — 8 колонок (CO, O3, NO2, SO2, PM2.5, PM10,
                            US EPA index, GB DEFRA index)

Решта колонок CSV (температура у °F, тиск у дюймах, місяць тощо) в ORM не описані —
завантажувач їх просто ігнорує (див. відповідь на питання 1 у README).
"""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from weather.domain.enums import WindDirection


class Base(DeclarativeBase):
    pass


class WeatherObservation(Base):
    """Одне спостереження погоди у певному місті у певний момент часу."""

    __tablename__ = "weather_observations"
    __table_args__ = (
        # одне місто не може мати два спостереження з однаковим last_updated —
        # це робить повторний імпорт CSV ідемпотентним
        UniqueConstraint("country", "location_name", "last_updated", name="uq_observation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- місце та час ---
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # --- загальні погодні показники ---
    temperature_celsius: Mapped[float] = mapped_column(Float, nullable=False)
    condition_text: Mapped[str] = mapped_column(String(100), nullable=False)
    humidity: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- вітер ---
    wind_kph: Mapped[float] = mapped_column(Float, nullable=False)
    wind_degree: Mapped[int] = mapped_column(Integer, nullable=False)
    wind_direction: Mapped[WindDirection] = mapped_column(
        Enum(WindDirection, name="wind_direction", native_enum=True), nullable=False
    )

    # --- схід/захід сонця ---
    sunrise: Mapped[time] = mapped_column(Time, nullable=False)
    sunset: Mapped[time] = mapped_column(Time, nullable=False)

    # --- стан повітря (варіант 2) — на етапі 2 переїдуть в окрему таблицю ---
    air_quality_carbon_monoxide: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_ozone: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_nitrogen_dioxide: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_sulphur_dioxide: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_pm2_5: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_pm10: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_us_epa_index: Mapped[int] = mapped_column(Integer, nullable=False)
    air_quality_gb_defra_index: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WeatherObservation {self.country}/{self.location_name} "
            f"@ {self.last_updated:%Y-%m-%d %H:%M}>"
        )
