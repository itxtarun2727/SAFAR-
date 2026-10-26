"""
reset_db.py — Database reset and re-seed utility for SAFAR portal.
Drops all existing tables and re-initializes fresh schema and demonstration data.
"""

import sys
from database import engine, Base, SessionLocal
import models
from seed import seed_all


def reset_and_seed():
    print("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables afresh from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    print("Seeding initial rules, universities, banks, institutions, users, and scenarios...")
    db = SessionLocal()
    try:
        seed_all(db)
        print("Database reset and reseed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    reset_and_seed()
