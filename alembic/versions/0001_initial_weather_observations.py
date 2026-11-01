"""Етап 1: початкова схема — одна плоска таблиця weather_observations

Revision ID: 0001
Revises:
Create Date: 2026-11-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

WIND_DIRECTIONS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


def wind_direction_enum() -> sa.Enum:
    # native_enum: у Postgres створюється тип ENUM wind_direction, у MySQL — ENUM(...)
    return sa.Enum(*WIND_DIRECTIONS, name="wind_direction", native_enum=True)


def upgrade() -> None:
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("location_name", sa.String(length=100), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.Column("temperature_celsius", sa.Float(), nullable=False),
        sa.Column("condition_text", sa.String(length=100), nullable=False),
        sa.Column("humidity", sa.Integer(), nullable=False),
        sa.Column("wind_kph", sa.Float(), nullable=False),
        sa.Column("wind_degree", sa.Integer(), nullable=False),
        sa.Column("wind_direction", wind_direction_enum(), nullable=False),
        sa.Column("sunrise", sa.Time(), nullable=False),
        sa.Column("sunset", sa.Time(), nullable=False),
        sa.Column("air_quality_carbon_monoxide", sa.Float(), nullable=False),
        sa.Column("air_quality_ozone", sa.Float(), nullable=False),
        sa.Column("air_quality_nitrogen_dioxide", sa.Float(), nullable=False),
        sa.Column("air_quality_sulphur_dioxide", sa.Float(), nullable=False),
        sa.Column("air_quality_pm2_5", sa.Float(), nullable=False),
        sa.Column("air_quality_pm10", sa.Float(), nullable=False),
        sa.Column("air_quality_us_epa_index", sa.Integer(), nullable=False),
        sa.Column("air_quality_gb_defra_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country", "location_name", "last_updated", name="uq_observation"),
    )
    op.create_index("ix_weather_observations_country", "weather_observations", ["country"])
    op.create_index("ix_weather_observations_last_updated", "weather_observations", ["last_updated"])


def downgrade() -> None:
    op.drop_index("ix_weather_observations_last_updated", table_name="weather_observations")
    op.drop_index("ix_weather_observations_country", table_name="weather_observations")
    op.drop_table("weather_observations")
    # drop_table не видаляє окремий тип ENUM у Postgres — робимо це явно
    wind_direction_enum().drop(op.get_bind(), checkfirst=True)
