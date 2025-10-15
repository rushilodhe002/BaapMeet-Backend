from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os


# No .env per spec; default DSN below. Adjust if needed.
# MySQL DSN (no .env as requested)
# Ensure MySQL is running and database `baapmeet` exists
DATABASE_URL = "mysql+pymysql://appuser:strong_password_here@localhost:3306/your_app_db"

class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

