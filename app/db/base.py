"""
Database engine and session setup
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from app.settings import settings

# Create engine
# Railway PostgreSQL has limited connections (~20-100) - keep pool small to avoid exhaustion
engine = create_engine(
    settings.active_database_url,
    pool_pre_ping=True,
    pool_size=5,           # Base persistent connections
    max_overflow=10,       # Max additional connections under load
    pool_timeout=30,       # Wait up to 30s for connection
    pool_recycle=60,       # Recycle connections every 60s to clear stale ones faster
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Database session context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a new database session (for dependency injection)"""
    return SessionLocal()


