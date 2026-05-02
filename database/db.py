import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker


DEFAULT_DATABASE_URL = "postgresql://postgres:tTG%2FiiHwQ_nG7-5@db.rsjhlslzsdwdfnlzcxfp.supabase.co:5432/postgres"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

Base = declarative_base()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db():
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
