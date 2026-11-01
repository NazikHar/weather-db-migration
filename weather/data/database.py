"""Створення engine та сесій SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from weather.config import get_database_url


def make_engine(url: str | None = None, echo: bool = False) -> Engine:
    """Engine для вказаного URL (за замовчуванням — основна база з конфігурації)."""
    return create_engine(url or get_database_url(), echo=echo, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Транзакційний контекст: commit при успіху, rollback при помилці."""
    session = make_session_factory(engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
