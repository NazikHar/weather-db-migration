"""ORM-моделі (SQLAlchemy 2.x, declarative).

Описано лише обрані колонки датасету Global Weather Repository (варіант 2 — стан повітря):

    обов'язкові типи      : country (текст), wind_degree (ціле), wind_kph (дробове),
                            wind_direction (enum), last_updated (дата-час), sunrise (час)
    категорія «стан повітря»: 8 колонок (CO, O3, NO2, SO2, PM2.5, PM10,
                            US EPA index, GB DEFRA index)

Етап 1: усе в одній плоскій таблиці weather_observations.
Етап 2: стан повітря винесено в таблицю air_quality (1:1, FK observation_id).

Решта колонок CSV (температура у °F, тиск у дюймах, місяць тощо) в ORM не описані —
завантажувач їх просто ігнорує (див. відповідь на питання 1 у README).
"""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from weather.domain.enums import WindDirection
from weather.domain.rules import AirQualityReading


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
    temperature_celsius: Mapped[float] = mapped_column(Float(53), nullable=False)
    condition_text: Mapped[str] = mapped_column(String(100), nullable=False)
    humidity: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- вітер ---
    wind_kph: Mapped[float] = mapped_column(Float(53), nullable=False)
    wind_degree: Mapped[int] = mapped_column(Integer, nullable=False)
    wind_direction: Mapped[WindDirection] = mapped_column(
        Enum(WindDirection, name="wind_direction", native_enum=True), nullable=False
    )

    # --- схід/захід сонця ---
    sunrise: Mapped[time] = mapped_column(Time, nullable=False)
    sunset: Mapped[time] = mapped_column(Time, nullable=False)

    # --- стан повітря (варіант 2): з етапу 2 — окрема таблиця, зв'язок 1:1 ---
    air_quality: Mapped["AirQuality | None"] = relationship(
        back_populates="observation", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WeatherObservation {self.country}/{self.location_name} "
            f"@ {self.last_updated:%Y-%m-%d %H:%M}>"
        )


class AirQuality(Base):
    """Стан повітря для одного спостереження (етап 2: винесено з weather_observations)."""

    __tablename__ = "air_quality"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("weather_observations.id", ondelete="CASCADE", name="fk_air_quality_observation"),
        nullable=False,
        unique=True,
    )

    carbon_monoxide: Mapped[float] = mapped_column(Float(53), nullable=False)   # CO, мкг/м³
    ozone: Mapped[float] = mapped_column(Float(53), nullable=False)             # O3, мкг/м³
    nitrogen_dioxide: Mapped[float] = mapped_column(Float(53), nullable=False)  # NO2, мкг/м³
    sulphur_dioxide: Mapped[float] = mapped_column(Float(53), nullable=False)   # SO2, мкг/м³
    pm2_5: Mapped[float] = mapped_column(Float(53), nullable=False)             # PM2.5, мкг/м³
    pm10: Mapped[float] = mapped_column(Float(53), nullable=False)              # PM10, мкг/м³
    us_epa_index: Mapped[int] = mapped_column(Integer, nullable=False)      # 1 (Good) … 6 (Hazardous)
    gb_defra_index: Mapped[int] = mapped_column(Integer, nullable=False)    # 1 (Low) … 10 (Very High)

    # Етап 3: «Чи варто виходити на вулицю». NULL — ще не обчислено (див. domain/rules.py)
    is_safe_to_go_outside: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Чи варто виходити на вулицю: NULL — не обчислено, true/false — так/ні",
    )

    observation: Mapped[WeatherObservation] = relationship(back_populates="air_quality")

    def as_reading(self) -> AirQualityReading:
        """Перетворити ORM-рядок у незалежний від БД об'єкт для бізнес-правила."""
        return AirQualityReading(us_epa_index=self.us_epa_index, pm2_5=self.pm2_5)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AirQuality obs={self.observation_id} EPA={self.us_epa_index} PM2.5={self.pm2_5}>"
