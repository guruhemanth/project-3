"""SQLAlchemy engine, session factory and declarative base."""
from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    """Return True if the database is reachable (used at app startup)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def ensure_all_tables() -> list[str]:
    """Verify every table declared on ``Base.metadata`` exists in the database.

    Any missing tables are created (idempotent). This is a defensive self-heal
    that runs at app startup so the server can boot even if a table was dropped
    or migrations never ran. It only creates *missing* tables -- it does not
    alter existing ones, so Alembic remains the source of truth for columns,
    indexes, and constraints.
    """
    # Ensure ORM models are registered on this Base (they import lazily to
    # avoid a circular import with this module).
    from . import models  # noqa: F401

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing = [t for name, t in Base.metadata.tables.items() if name not in existing]
    if not missing:
        return []
    Base.metadata.create_all(engine, tables=missing, checkfirst=True)
    return [t.name for t in missing]
