from sqlalchemy import create_engine

from pathlib import Path
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
from dotenv import load_dotenv, find_dotenv

from dotenv import load_dotenv, find_dotenv
import os

# DEBUG: show where Python thinks it’s loading from
# In Azure App Service, set DATABASE_URL in Configuration → Application settings
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is not set")

# 3. grab the URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set! Check that .env is in the project root.")

# 4. ensure sslmode
if "sslmode=" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"
engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy session
    and ensures it’s closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
