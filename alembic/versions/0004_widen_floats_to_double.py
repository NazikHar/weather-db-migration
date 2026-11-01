"""Етап 5: розширити дробові колонки до подвійної точності (переносимість Postgres <-> MySQL)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-01

Проблема, виявлена при накочуванні міграцій на MySQL: sa.Float() без точності
компілюється у Postgres як DOUBLE PRECISION (8 байт), а в MySQL — як FLOAT (4 байти,
~7 значущих цифр). Дані при перенесенні округлялися б (наприклад 2887.8 -> 2887.80005),
і контрольні суми двох баз не збігалися б.

Рішення: sa.Float(precision=53) -> DOUBLE PRECISION в обох СУБД.
У Postgres ця міграція фактично нічого не змінює (тип уже double precision),
у MySQL — ALTER COLUMN ... DOUBLE. Дані не втрачаються (розширення типу).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

FLOAT_COLUMNS = {
    "weather_observations": ("temperature_celsius", "wind_kph"),
    "air_quality": (
        "carbon_monoxide", "ozone", "nitrogen_dioxide", "sulphur_dioxide", "pm2_5", "pm10",
    ),
}


def _alter(from_type: sa.types.TypeEngine, to_type: sa.types.TypeEngine) -> None:
    for table, columns in FLOAT_COLUMNS.items():
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.alter_column(
                    column, existing_type=from_type, type_=to_type, existing_nullable=False
                )


def upgrade() -> None:
    _alter(sa.Float(), sa.Float(precision=53))


def downgrade() -> None:
    _alter(sa.Float(precision=53), sa.Float())
