"""Engine, request-scoped sessions, and schema setup.

Apply the schema to the app database (as techforce_owner):
    uv run python -m app.db            # add --reset to drop the tables first
The test suite applies it to the test database itself (backend/tests/conftest.py).
"""
import argparse
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

DB_DIR = Path(__file__).resolve().parents[2] / "db"
SCHEMA_FILE = DB_DIR / "schema.sql"

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(engine)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def apply_schema(owner_url: str, *, reset: bool = False) -> None:
    """Create the tables and grants as the owner role, in one transaction.

    schema.sql is static SQL with no parameters or interpolation, so it is sent as-is
    through the driver, which accepts several statements per call only in that case.
    """
    owner_engine = create_engine(owner_url)
    try:
        with owner_engine.begin() as conn:
            if reset:
                Base.metadata.drop_all(conn)
            conn.connection.driver_connection.execute(SCHEMA_FILE.read_text())
    finally:
        owner_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply db/schema.sql to the app database.")
    parser.add_argument("--reset", action="store_true", help="drop the tables first")
    apply_schema(settings.owner_database_url, reset=parser.parse_args().reset)
    print("schema applied to the app database")
