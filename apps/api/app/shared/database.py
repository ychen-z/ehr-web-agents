from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.shared.config import Settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine(settings: Settings | None = None):
    global _engine
    if settings is not None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory(engine=None):
    global _SessionLocal
    if engine is not None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db():
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database not initialized. Call get_engine() and get_session_factory() first.")
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()
