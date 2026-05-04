import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from utils import logger

load_dotenv()

# We no longer hardcode a default so the code fails properly if the user forgets to set it
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")

Base = declarative_base()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db():
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
