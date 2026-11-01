"""Репозиторії — єдине місце, де формуються SQL-запити до таблиць."""

from __future__ import annotations

from typing import Iterable, Iterator, Sequence

from sqlalchemy import func, select, update
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

    def count_unfilled(self) -> int:
        """Скільки рядків ще не мають відповіді «чи варто виходити» (NULL)."""
        return (
            self.session.scalar(
                select(func.count())
                .select_from(AirQuality)
                .where(AirQuality.is_safe_to_go_outside.is_(None))
            )
            or 0
        )

    def iter_unfilled(self, batch_size: int = 10_000) -> Iterator[Sequence[AirQuality]]:
        """Пачками віддає рядки з is_safe_to_go_outside IS NULL (keyset-пагінація за id)."""
        last_id = 0
        while True:
            rows = self.session.scalars(
                select(AirQuality)
                .where(AirQuality.is_safe_to_go_outside.is_(None), AirQuality.id > last_id)
                .order_by(AirQuality.id)
                .limit(batch_size)
            ).all()
            if not rows:
                return
            last_id = rows[-1].id
            yield rows

    def bulk_set_flag(self, values: Iterable[tuple[int, bool]]) -> int:
        """Масове UPDATE за первинним ключем (ORM bulk update by primary key, executemany)."""
        params = [{"id": i, "is_safe_to_go_outside": f} for i, f in values]
        if params:
            self.session.execute(update(AirQuality), params)
        return len(params)

    def reset_flags(self) -> None:
        self.session.execute(update(AirQuality).values(is_safe_to_go_outside=None))

    def flag_distribution(self) -> dict[bool | None, int]:
        rows = self.session.execute(
            select(AirQuality.is_safe_to_go_outside, func.count()).group_by(
                AirQuality.is_safe_to_go_outside
            )
        )
        return {flag: n for flag, n in rows}
