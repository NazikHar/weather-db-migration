"""Етап 2: винести стан повітря в окрему таблицю air_quality (без втрати даних)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01

Схема рефакторингу (expand → migrate → contract):
  1. expand   — створити нову таблицю air_quality (1:1 до weather_observations);
  2. migrate  — INSERT ... SELECT: скопіювати 8 колонок з weather_observations;
  3. contract — видалити ці 8 колонок зі старої таблиці.
downgrade() виконує ті самі кроки у зворотному порядку, тож дані не губляться
в жодному напрямку.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

AIR_QUALITY_COLUMNS = (
    ("carbon_monoxide", sa.Float()),
    ("ozone", sa.Float()),
    ("nitrogen_dioxide", sa.Float()),
    ("sulphur_dioxide", sa.Float()),
    ("pm2_5", sa.Float()),
    ("pm10", sa.Float()),
    ("us_epa_index", sa.Integer()),
    ("gb_defra_index", sa.Integer()),
)


def upgrade() -> None:
    # 1. expand
    op.create_table(
        "air_quality",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=False),
        *[sa.Column(name, type_, nullable=False) for name, type_ in AIR_QUALITY_COLUMNS],
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["weather_observations.id"],
            name="fk_air_quality_observation",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("observation_id", name="uq_air_quality_observation"),
    )

    # 2. migrate — один переносимий SQL-вираз, однаковий для Postgres і MySQL
    new_cols = ", ".join(name for name, _ in AIR_QUALITY_COLUMNS)
    old_cols = ", ".join(f"air_quality_{name}" for name, _ in AIR_QUALITY_COLUMNS)
    op.execute(
        f"INSERT INTO air_quality (observation_id, {new_cols}) "
        f"SELECT id, {old_cols} FROM weather_observations ORDER BY id"
    )

    # 3. contract
    with op.batch_alter_table("weather_observations") as batch:
        for name, _ in AIR_QUALITY_COLUMNS:
            batch.drop_column(f"air_quality_{name}")


def downgrade() -> None:
    # 1. повернути колонки (тимчасово nullable, щоб можна було додати їх до наявних рядків)
    with op.batch_alter_table("weather_observations") as batch:
        for name, type_ in AIR_QUALITY_COLUMNS:
            batch.add_column(sa.Column(f"air_quality_{name}", type_, nullable=True))

    # 2. перенести дані назад (корельований UPDATE — працює і в Postgres, і в MySQL)
    for name, _ in AIR_QUALITY_COLUMNS:
        op.execute(
            f"UPDATE weather_observations SET air_quality_{name} = "
            f"(SELECT a.{name} FROM air_quality a WHERE a.observation_id = weather_observations.id)"
        )

    # 3. повернути NOT NULL та прибрати нову таблицю
    with op.batch_alter_table("weather_observations") as batch:
        for name, type_ in AIR_QUALITY_COLUMNS:
            batch.alter_column(f"air_quality_{name}", existing_type=type_, nullable=False)
    op.drop_table("air_quality")
