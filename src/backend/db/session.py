from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings

settings = get_settings()

connect_args = {}
db_url = settings.database_url
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if ":///./" in db_url:
        db_path = Path(db_url.split(":///./", 1)[1])
        db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
