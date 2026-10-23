"""SQLAlchemy mappings. db/schema.sql is the source of truth (constraints, grants);
these mirror its columns for queries and are never used to create tables."""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Recruiter(Base):
    __tablename__ = "recruiters"

    recruiter_id: Mapped[str] = mapped_column(Text, primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True)
    role: Mapped[str] = mapped_column(Text)
    assigned_regions: Mapped[list[str]] = mapped_column(JSONB)


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id: Mapped[str] = mapped_column(Text, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text)
    region_code: Mapped[str] = mapped_column(Text)
    desired_role: Mapped[str | None] = mapped_column(Text)
    salary_expectation: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    applied_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
