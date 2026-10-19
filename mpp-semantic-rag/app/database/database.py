
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Local development uses SQLite by default.
# Render will provide DATABASE_URL for PostgreSQL.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./smartbin.db",
)

# Render PostgreSQL URLs may use either of these prefixes.
# Explicitly select psycopg 3, which is in requirements.txt.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

# SQLite needs a special connection argument; PostgreSQL does not.
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
