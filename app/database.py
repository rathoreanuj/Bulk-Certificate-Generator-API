"""
app/database.py - SQLAlchemy engine, session factory, and Base declarative class.

Features for production readiness & scalability:
  - SQLite Write-Ahead Logging (WAL) and synchronous=NORMAL enabled automatically,
    allowing concurrent readers and writers without database locking issues.
  - Busy timeout configured to 15 seconds to prevent 'database is locked' errors.
  - Production connection pooling parameters (pool_pre_ping, pool_size, pool_recycle)
    for PostgreSQL / MySQL support when DATABASE_URL is swapped.
  - Safe session dependency with automatic cleanup on request completion.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# Engine configuration depending on database dialect
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 15,
    }
else:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable Write-Ahead Logging and busy timeout for concurrent access."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """
    FastAPI dependency yielding a database session and ensuring closure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
