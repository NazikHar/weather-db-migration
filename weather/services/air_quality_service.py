"""Заповнення колонки air_quality.is_safe_to_go_outside.

Саме тут (у сервісному шарі) живе застосування правила з domain/rules.py до даних:
сервіс читає рядки з NULL-прапорцем пачками, обчислює відповідь чистою функцією
is_safe_to_go_outside() і масово оновлює БД. Міграція 0003 лише додала колонку.

Також цей сервіс викликається імпортом після вставки нових рядків (див. import_service),
тому свіжозавантажені дані теж одразу отримують відповідь.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine

from weather.data.database import session_scope
from weather.data.repositories import AirQualityRepository
from weather.domain.rules import is_safe_to_go_outside


@dataclass
class FillReport:
    updated: int
    safe: int
    unsafe: int


class AirQualityService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def fill_is_safe_to_go_outside(self, only_missing: bool = True, progress=print) -> FillReport:
        """Обчислити прапорець для всіх рядків, де він ще NULL (або для всіх, якщо only_missing=False)."""
        updated = safe = 0
        with session_scope(self.engine) as session:
            repo = AirQualityRepository(session)
            if not only_missing:
                repo.reset_flags()  # повний перерахунок: скинути все в NULL
            total = repo.count_unfilled()
            for batch in repo.iter_unfilled():
                values = [(row.id, is_safe_to_go_outside(row.as_reading())) for row in batch]
                updated += repo.bulk_set_flag(values)
                safe += sum(1 for _, f in values if f)
                session.expunge_all()
                progress(f"  обчислено {updated}/{total}")
        return FillReport(updated=updated, safe=safe, unsafe=updated - safe)

    def distribution(self) -> dict[bool | None, int]:
        with session_scope(self.engine) as session:
            return AirQualityRepository(session).flag_distribution()
