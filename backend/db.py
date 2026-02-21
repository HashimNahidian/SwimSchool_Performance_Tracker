from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

<<<<<<< HEAD
from config import settings

engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)
=======
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://propel:propelpass@localhost:5432/propel_eval",
)

SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

engine = create_engine(DATABASE_URL, echo=SQL_ECHO)
>>>>>>> origin/main
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


<<<<<<< HEAD
def get_db() -> Generator[Session, None, None]:
=======
def get_db():
>>>>>>> origin/main
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
