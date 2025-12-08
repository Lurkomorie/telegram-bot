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
    pool_size=3,           # Reduced from 5 - base persistent connections
    max_overflow=5,        # Reduced from 10 - max additional connections under load
    pool_timeout=10,       # Fail fast if pool exhausted (10 seconds wait max)
    pool_recycle=300,      # Recycle connections after 5 minutes to avoid stale connections
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


