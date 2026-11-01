"""Конфігурація застосунку: рядки підключення до БД беруться зі змінних оточення.

Підтримується файл .env у корені проєкту (через python-dotenv, якщо встановлено).
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:  # python-dotenv не є обов'язковим
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

DEFAULT_DATABASE_URL = "postgresql+psycopg2://weather:weather@localhost:5432/weather_pg"
DEFAULT_TARGET_DATABASE_URL = (
    "mysql+pymysql://weather:weather@localhost:3306/weather_mysql?charset=utf8mb4"
)


def get_database_url() -> str:
    """URL основної бази (з якою працюють ORM, міграції та CLI)."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_target_database_url() -> str:
    """URL цільової бази для перенесення даних (етап 5)."""
    return os.environ.get("TARGET_DATABASE_URL", DEFAULT_TARGET_DATABASE_URL)


def default_csv_path() -> Path:
    """Шлях до CSV за замовчуванням: повний датасет, якщо є, інакше вибірка."""
    full = PROJECT_ROOT / "data" / "GlobalWeatherRepository.csv"
    return full if full.exists() else PROJECT_ROOT / "data" / "sample_weather.csv"
