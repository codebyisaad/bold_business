"""Engine, request-scoped sessions, and schema setup.

Apply the schema (as techforce_owner):
    uv run python -m app.db            # app database
    uv run python -m app.db --test     # test database
    add --reset to drop the tables first
"""
import argparse
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

DB_DIR = Path(__file__).resolve().parents[2] / "db"
SCHEMA_FILES = (DB_DIR / "schema.sql", DB_DIR / "seed.sql")

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(engine)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def apply_schema(owner_url: str, *, reset: bool = False) -> None:
    """Create the tables, grants and recruiter seed as the owner role, in one transaction.

    The files are static SQL with no parameters or interpolation, so they are sent as-is
    through the driver, which accepts several statements per call only in that case.
    """
    owner_engine = create_engine(owner_url)
    try:
        with owner_engine.begin() as conn:
            if reset:
                Base.metadata.drop_all(conn)
            driver_conn = conn.connection.driver_connection
            for path in SCHEMA_FILES:
                driver_conn.execute(path.read_text())
    finally:
        owner_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply db/schema.sql and db/seed.sql.")
    parser.add_argument("--test", action="store_true", help="target the test database")
    parser.add_argument("--reset", action="store_true", help="drop the tables first")
    args = parser.parse_args()
    url = settings.test_owner_database_url if args.test else settings.owner_database_url
    apply_schema(url, reset=args.reset)
    print(f"schema applied to the {'test' if args.test else 'app'} database")
