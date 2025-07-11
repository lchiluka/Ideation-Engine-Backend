# db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from settings import Settings

# ─── Load settings ─────────────────────────────────────────────────────────────
# Pydantic will read .env locally or actual env vars in Azure App Service
settings = Settings()

# ─── Build the full DATABASE_URL ───────────────────────────────────────────────
db_url = str(settings.DATABASE_URL)   # type: ignore
if "sslmode=" not in db_url:
    # ensure SSL on Azure Postgres
    sep = "&" if "?" in db_url else "?"
    db_url = f"{db_url}{sep}sslmode=require"

# ─── Create Engine & Session ───────────────────────────────────────────────────
# pool_pre_ping helps recover dropped connections
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ─── Base Model for your ORM classes ────────────────────────────────────────────
Base = declarative_base()

# ─── FastAPI Dependency ────────────────────────────────────────────────────────
def get_db():
    """
    Yields a SQLAlchemy Session, and ensures closure after each request.
    Usage in FastAPI routes:
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
