"""Етап 3: булева колонка air_quality.is_safe_to_go_outside («Чи варто виходити на вулицю»)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-01

Колонка створюється БЕЗ значення за замовчуванням (NULL = «ще не обчислено»).
Обчислення — відповідальність сервісного шару (weather.services.air_quality_service),
де застосовується правило з weather.domain.rules; міграція лише змінює схему.
Так формула існує в одному місці, а не дублюється в SQL міграції.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("air_quality") as batch:
        batch.add_column(
            sa.Column(
                "is_safe_to_go_outside",
                sa.Boolean(),
                nullable=True,
                comment="Чи варто виходити на вулицю: NULL — не обчислено, true/false — так/ні",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("air_quality") as batch:
        batch.drop_column("is_safe_to_go_outside")
