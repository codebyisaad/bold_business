from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from app.domain import normalize
from app.domain.normalize import Region, Status

REQUIRED_FIELDS = ("candidate_id", "first_name", "last_name", "email", "region_code", "status")


def _apply(field: str, rule: Callable[[str], Any], raw: Any) -> Any:
    """Run one normalize rule on a raw CSV string, turning its ValueError into a
    validation error whose message is the reason shown in the import report."""
    if not isinstance(raw, str):
        return raw
    if field in REQUIRED_FIELDS and not raw.strip():
        raise PydanticCustomError("missing", "{reason}", {"reason": f"{field} is missing"})
    try:
        return rule(raw)
    except ValueError as exc:
        raise PydanticCustomError("invalid", "{reason}", {"reason": str(exc)}) from None


class CandidateRow(BaseModel):
    """One valid, normalized candidate. Built from a raw CSV row with model_validate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    region_code: Region
    desired_role: str | None
    salary_expectation: Decimal | None
    applied_date: date | None
    status: Status
    source: str | None
    notes: str | None

    @field_validator("candidate_id", "first_name", "last_name", "desired_role", "source", mode="before")
    @classmethod
    def _text(cls, raw: Any, info) -> Any:
        return _apply(info.field_name, normalize.collapse, raw)

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, raw: Any) -> Any:
        return _apply("email", normalize.email, raw)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, raw: Any) -> Any:
        return _apply("phone", normalize.phone, raw)

    @field_validator("region_code", mode="before")
    @classmethod
    def _region(cls, raw: Any) -> Any:
        return _apply("region_code", normalize.region, raw)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, raw: Any) -> Any:
        return _apply("status", normalize.status, raw)

    @field_validator("applied_date", mode="before")
    @classmethod
    def _applied_date(cls, raw: Any) -> Any:
        return _apply("applied_date", normalize.applied_date, raw)

    @field_validator("salary_expectation", mode="before")
    @classmethod
    def _salary(cls, raw: Any) -> Any:
        return _apply("salary_expectation", normalize.salary, raw)

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, raw: Any) -> Any:
        # Stored exactly as written; only an empty or all-whitespace note becomes null.
        return raw if not isinstance(raw, str) or raw.strip() else None


class RejectedRow(BaseModel):
    row: int
    reason: str


class MergedRow(BaseModel):
    row: int
    into_row: int


class ImportReport(BaseModel):
    """Response body of POST /api/v1/candidates/import."""

    imported: int
    merged: int
    updated: int
    rejected: list[RejectedRow]


class ImportPlan(BaseModel):
    """What the pure importer decided. The writer persists inserts and updates."""

    inserts: list[CandidateRow]
    updates: list[CandidateRow]
    merged: list[MergedRow]
    rejected: list[RejectedRow]

    def report(self) -> ImportReport:
        return ImportReport(
            imported=len(self.inserts),
            merged=len(self.merged),
            updated=len(self.updates),
            rejected=sorted(self.rejected, key=lambda r: r.row),
        )
