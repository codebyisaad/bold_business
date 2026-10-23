"""The pure half of the import: bytes in, an ImportPlan out. No database access.
The rules are DECISIONS.md sections 8-10."""
import csv
import io
from collections.abc import Iterable

from pydantic import ValidationError

from app.domain.schemas import CandidateRow, ImportPlan, MergedRow, RejectedRow

COLUMNS = tuple(CandidateRow.model_fields)

RawRow = tuple[int, dict[str, str]]


class BadFileError(ValueError):
    """The whole upload is refused before any row is processed."""


def parse_csv(data: bytes) -> list[RawRow]:
    """Return (spreadsheet row number, raw values) pairs. The header is row 1."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BadFileError("file is not valid UTF-8") from None
    if not text.strip():
        raise BadFileError("file is empty")

    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
        _check_header(header)
        rows = []
        for row_number, values in enumerate(reader, start=2):
            if len(values) != len(header):
                raise BadFileError(
                    f"row {row_number} has {len(values)} fields, expected {len(header)}")
            rows.append((row_number, dict(zip(header, values))))
    except csv.Error as exc:
        raise BadFileError(f"file is not valid CSV: {exc}") from None
    if not rows:
        raise BadFileError("file has a header but no candidate rows")
    return rows


def _check_header(header: list[str]) -> None:
    problems = []
    if missing := [c for c in COLUMNS if c not in header]:
        problems.append(f"missing {', '.join(missing)}")
    if extra := sorted(set(header) - set(COLUMNS)):
        problems.append(f"unexpected {', '.join(extra)}")
    if duplicated := sorted({c for c in header if header.count(c) > 1}):
        problems.append(f"duplicated {', '.join(duplicated)}")
    if problems:
        raise BadFileError("header must be exactly the 12 candidate columns: " + "; ".join(problems))


def plan_import(rows: Iterable[RawRow], existing: Iterable[tuple[str, str]]) -> ImportPlan:
    """Decide what to insert, update, merge and reject.

    existing: (candidate_id, email) pairs already in the database that share an email
    or a candidate_id with the file.
    """
    rejected: list[RejectedRow] = []

    # 1. Validate every row. Invalid rows take no further part.
    valid: list[tuple[int, dict[str, str], CandidateRow]] = []
    for row_number, raw in rows:
        try:
            valid.append((row_number, raw, CandidateRow.model_validate(raw)))
        except ValidationError as exc:
            reason = "; ".join(error["msg"] for error in exc.errors())
            rejected.append(RejectedRow(row=row_number, reason=reason))

    # 2. Dedup in file order.
    stored_email_by_id = dict(existing)
    merged: list[MergedRow] = []
    first_row_by_raw: dict[tuple[str, ...], int] = {}
    kept: dict[str, tuple[int, CandidateRow]] = {}  # email -> first row with that email
    id_owner: dict[str, tuple[int, str]] = {}      # candidate_id -> (row, email)

    for row_number, raw, candidate in valid:
        raw_key = tuple(raw.values())
        if raw_key in first_row_by_raw:  # 2.1 exact duplicate
            merged.append(MergedRow(row=row_number, into_row=first_row_by_raw[raw_key]))
            continue
        first_row_by_raw[raw_key] = row_number

        if candidate.email in kept:  # 2.2 same email: fill blanks of the first row only
            first_row, first = kept[candidate.email]
            kept[candidate.email] = (first_row, _fill_blanks(first, candidate))
            merged.append(MergedRow(row=row_number, into_row=first_row))
            continue

        cid = candidate.candidate_id
        if cid in id_owner and id_owner[cid][1] != candidate.email:  # 2.3
            rejected.append(RejectedRow(
                row=row_number, reason=f"candidate_id {cid} already belongs to row {id_owner[cid][0]}"))
            continue
        if cid in stored_email_by_id and stored_email_by_id[cid] != candidate.email:  # 2.4
            rejected.append(RejectedRow(
                row=row_number, reason=f"candidate_id {cid} already belongs to a different candidate"))
            continue

        id_owner[cid] = (row_number, candidate.email)
        kept[candidate.email] = (row_number, candidate)

    # 3. Classify. An email already stored is an update (blank-filling only, done by the writer).
    stored_emails = set(stored_email_by_id.values())
    inserts = [c for _, c in kept.values() if c.email not in stored_emails]
    updates = [c for _, c in kept.values() if c.email in stored_emails]
    return ImportPlan(inserts=inserts, updates=updates, merged=merged, rejected=rejected)


def _fill_blanks(target: CandidateRow, source: CandidateRow) -> CandidateRow:
    filled = {
        field: getattr(source, field)
        for field in COLUMNS
        if getattr(target, field) is None and getattr(source, field) is not None
    }
    return target.model_copy(update=filled)
