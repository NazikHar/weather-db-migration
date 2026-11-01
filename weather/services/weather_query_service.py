"""Запит «уся погода за країною та датою» (етап 4).

Сервіс повертає DTO (прості dataclass-и), а не ORM-об'єкти, щоб шар представлення
не залежав від SQLAlchemy і від того, що дані лежать у двох таблицях.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.engine import Engine

from weather.data.database import session_scope
from weather.data.repositories import WeatherObservationRepository
from weather.domain.rules import explain


@dataclass(frozen=True)
class WeatherReport:
    """Повна інформація про одне спостереження — усе, що є в базі."""

    # загальна погода
    country: str
    city: str
    last_updated: datetime
    temperature_celsius: float
    condition_text: str
    humidity: int
    wind_kph: float
    wind_degree: int
    wind_direction: str
    sunrise: time
    sunset: time
    # стан повітря (варіант 2)
    carbon_monoxide: float
    ozone: float
    nitrogen_dioxide: float
    sulphur_dioxide: float
    pm2_5: float
    pm10: float
    us_epa_index: int
    gb_defra_index: int
    # етап 3
    is_safe_to_go_outside: bool | None
    go_outside_explanation: str


@dataclass(frozen=True)
class QueryResult:
    reports: list[WeatherReport]
    country_suggestions: list[str]  # заповнюється, якщо нічого не знайдено


class WeatherQueryService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def by_country_and_date(
        self,
        country: str,
        day: date,
        city: str | None = None,
        safe_only: bool | None = None,
    ) -> QueryResult:
        with session_scope(self.engine) as session:
            repo = WeatherObservationRepository(session)
            rows = repo.find(country=country, day=day, city=city, safe_only=safe_only)
            reports = [self._to_report(obs) for obs in rows]
            suggestions = [] if reports else list(repo.countries_like(country[:3]))
            return QueryResult(reports=reports, country_suggestions=suggestions)

    @staticmethod
    def _to_report(obs) -> WeatherReport:
        aq = obs.air_quality
        return WeatherReport(
            country=obs.country,
            city=obs.location_name,
            last_updated=obs.last_updated,
            temperature_celsius=obs.temperature_celsius,
            condition_text=obs.condition_text,
            humidity=obs.humidity,
            wind_kph=obs.wind_kph,
            wind_degree=obs.wind_degree,
            wind_direction=obs.wind_direction.value,
            sunrise=obs.sunrise,
            sunset=obs.sunset,
            carbon_monoxide=aq.carbon_monoxide,
            ozone=aq.ozone,
            nitrogen_dioxide=aq.nitrogen_dioxide,
            sulphur_dioxide=aq.sulphur_dioxide,
            pm2_5=aq.pm2_5,
            pm10=aq.pm10,
            us_epa_index=aq.us_epa_index,
            gb_defra_index=aq.gb_defra_index,
            is_safe_to_go_outside=aq.is_safe_to_go_outside,
            go_outside_explanation=explain(aq.as_reading()),
        )
