"""The database itself: roles, grants, seed and constraints. Real test database."""
import pytest
from sqlalchemy import column, delete, func, select, table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models import Candidate, Recruiter
from app.seed import RECRUITERS_CSV, read_recruiters

pg_roles = table("pg_roles", column("rolname"), column("rolsuper"), column("rolbypassrls"))
pg_tables = table("pg_tables", column("tablename"), column("tableowner"), column("schemaname"))


def test_app_role_is_not_superuser_and_cannot_bypass_rls(db):
    with db.connect() as conn:
        role = conn.execute(select(pg_roles).where(pg_roles.c.rolname == func.current_user())).one()
    assert (role.rolname, role.rolsuper, role.rolbypassrls) == ("techforce_app", False, False)


def test_app_role_owns_no_table(db):
    with db.connect() as conn:
        owners = dict(conn.execute(
            select(pg_tables.c.tablename, pg_tables.c.tableowner).where(pg_tables.c.schemaname == "public")).all())
    assert owners == {"candidates": "techforce_owner", "recruiters": "techforce_owner"}


def test_app_role_cannot_delete_candidates(db):
    with db.connect() as conn, pytest.raises(ProgrammingError, match="permission denied"):
        conn.execute(delete(Candidate))


def test_app_role_cannot_write_recruiters(db):
    with db.connect() as conn, pytest.raises(ProgrammingError, match="permission denied"):
        conn.execute(delete(Recruiter))


def test_seeded_recruiters_match_the_csv(db):
    with db.connect() as conn:
        stored = [dict(row._mapping) for row in conn.execute(select(Recruiter).order_by(Recruiter.recruiter_id))]
    assert stored == read_recruiters(RECRUITERS_CSV)


@pytest.mark.parametrize("role, regions", [
    ("admin", ["US-MW"]),          # admin without *
    ("recruiter", ["*"]),          # * without admin
    ("recruiter", ["us-mw"]),      # not a canonical code
    ("recruiter", []),             # no regions
])
def test_recruiter_constraints(owner_engine, role, regions):
    stmt = insert(Recruiter).values(
        recruiter_id="R-900", full_name="Test", email="test@techforce-demo.com",
        role=role, assigned_regions=regions)
    with pytest.raises(IntegrityError, match="check constraint"), owner_engine.begin() as conn:
        conn.execute(stmt)
