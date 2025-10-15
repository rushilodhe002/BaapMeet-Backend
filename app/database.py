from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# No .env per spec; default DSN below. Adjust if needed.
# MySQL DSN (no .env as requested)
# Ensure MySQL is running and database `baapmeet` exists
DATABASE_URL = "mysql+pymysql://root:9699@localhost:3306/baapmeet?charset=utf8mb4"


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True, isolation_level="AUTOCOMMIT")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

