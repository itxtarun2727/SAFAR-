"""
database.py — Database connection, session factory, and declarative Base.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Automatically load .env from backend/ or project root
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    if not DEMO_MODE:
        raise RuntimeError("DATABASE_URL environment variable is strictly required in non-demo mode.")
    DATABASE_URL = "sqlite:///./safar.db"

# Handle Render postgres:// legacy format and explicitly bind psycopg2 driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Handle sqlite fallback for local unit tests without docker
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency to provide a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
