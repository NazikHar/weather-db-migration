"""Перенесення даних між двома базами (етап 5: Postgres -> MySQL) та їх звірка.

Схему на цільовій базі створюють ті самі Alembic-міграції (DATABASE_URL=<mysql>; alembic upgrade head).
Цей сервіс переносить лише ДАНІ, зберігаючи первинні ключі, щоб обидві бази були
ідентичні до рядка (FK observation_id вказує на ті самі id).

Робота ведеться через SQLAlchemy Core (Table-об'єкти з ORM-метаданих), а не через ORM-сесію:
так можна явно вставляти id та копіювати пачками без накладних витрат identity map.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine

from weather.data.models import AirQuality, Base, WeatherObservation

# порядок важливий: батьківська таблиця перед дочірньою (FK)
TABLES = (WeatherObservation.__table__, AirQuality.__table__)
BATCH_SIZE = 5_000


@dataclass
class TransferReport:
    copied: dict[str, int] = field(default_factory=dict)


@dataclass
class TableCheck:
    table: str
    source_count: int
    target_count: int
    source_digest: str
    target_digest: str

    @property
    def ok(self) -> bool:
        return self.source_count == self.target_count and self.source_digest == self.target_digest


class TransferService:
    def __init__(self, source: Engine, target: Engine) -> None:
        self.source = source
        self.target = target

    # ---------------------------------------------------------------- copy
    def copy_all(self, truncate_target: bool = True, progress=print) -> TransferReport:
        report = TransferReport()
        with self.source.connect() as src, self.target.begin() as dst:
            if truncate_target:
                self._truncate(dst)
            for table in TABLES:
                total = src.scalar(select(func.count()).select_from(table)) or 0
                copied = 0
                # server-side cursor: не тягнемо 100k рядків у пам'ять одразу
                result = src.execution_options(stream_results=True).execute(
                    select(table).order_by(table.c.id)
                )
                while batch := result.fetchmany(BATCH_SIZE):
                    rows = [dict(r._mapping) for r in batch]
                    dst.execute(table.insert(), rows)
                    copied += len(rows)
                    progress(f"  {table.name}: {copied}/{total}")
                report.copied[table.name] = copied
            self._fix_sequences(dst)
        return report

    def _truncate(self, conn) -> None:
        for table in reversed(TABLES):  # дочірня перед батьківською
            conn.execute(table.delete())

    def _fix_sequences(self, conn) -> None:
        """Після вставки з явними id синхронізувати лічильники автоінкременту.

        Postgres: sequence не рухається при явному id -> setval.
        MySQL/MariaDB: AUTO_INCREMENT сам підтягується до max(id)+1 — нічого робити не треба.
        """
        if conn.dialect.name == "postgresql":
            for table in TABLES:
                conn.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
                    )
                )

    # -------------------------------------------------------------- verify
    def verify(self) -> list[TableCheck]:
        """Порівняти кількість рядків і SHA-256 від канонічного дампа кожної таблиці."""
        checks = []
        for table in TABLES:
            s_count, s_digest = self._digest(self.source, table)
            t_count, t_digest = self._digest(self.target, table)
            checks.append(TableCheck(table.name, s_count, t_count, s_digest, t_digest))
        return checks

    @staticmethod
    def _canonical(value) -> str:
        """Нормалізація значень, щоб Postgres і MySQL давали однаковий рядок."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, float):
            return repr(round(value, 6))
        if hasattr(value, "value"):  # Enum -> його рядок
            return str(value.value)
        if hasattr(value, "isoformat"):  # datetime / time
            return value.isoformat()
        return str(value)

    def _digest(self, engine: Engine, table) -> tuple[int, str]:
        h = hashlib.sha256()
        count = 0
        with engine.connect() as conn:
            result = conn.execution_options(stream_results=True).execute(
                select(table).order_by(table.c.id)
            )
            for row in result:
                count += 1
                h.update("|".join(self._canonical(v) for v in row).encode("utf-8"))
                h.update(b"\n")
        return count, h.hexdigest()

    @staticmethod
    def tables_in_metadata() -> list[str]:
        return list(Base.metadata.tables)
