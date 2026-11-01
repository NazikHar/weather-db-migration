"""Репозиторії — єдине місце, де формуються SQL-запити до таблиць."""

from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from weather.data.models import AirQuality, WeatherObservation


class WeatherObservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(WeatherObservation)) or 0

    def existing_keys(self) -> set[tuple[str, str, object]]:
        """Множина натуральних ключів (country, location_name, last_updated) у БД."""
        rows = self.session.execute(
            select(
                WeatherObservation.country,
                WeatherObservation.location_name,
                WeatherObservation.last_updated,
            )
        )
        return {tuple(r) for r in rows}

    def add_all(self, observations: Iterable[WeatherObservation]) -> int:
        """Додати ORM-об'єкти (разом із пов'язаними AirQuality) і скинути в БД."""
        observations = list(observations)
        self.session.add_all(observations)
        self.session.flush()
        return len(observations)

    def all(self, limit: int | None = None) -> Sequence[WeatherObservation]:
        stmt = (
            select(WeatherObservation)
            .options(selectinload(WeatherObservation.air_quality))
            .order_by(WeatherObservation.id)
        )
        if limit:
            stmt = stmt.limit(limit)
        return self.session.scalars(stmt).all()


class AirQualityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(AirQuality)) or 0
