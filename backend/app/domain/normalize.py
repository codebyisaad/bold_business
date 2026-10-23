"""One pure function per field. Each returns the normalized value or raises ValueError
with a reason a recruiter can read. The rules are DECISIONS.md sections 2-7."""
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from email_validator import EmailNotValidError, validate_email


class Region(StrEnum):
    US_MW = "US-MW"
    US_NE = "US-NE"
    US_SE = "US-SE"
    US_W = "US-W"
    PH_MNL = "PH-MNL"
    CO_BOG = "CO-BOG"


class Status(StrEnum):
    ACTIVE = "active"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    WITHDRAWN = "withdrawn"
    HIRED = "hired"
    REJECTED = "rejected"


_REGION_KEYS = {region.value.replace("-", ""): region for region in Region}
_MONTHS = {name: number for number, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1)}
_SALARY_NULL_WORDS = {"negotiable", "na", "n/a", "tbd"}
_SALARY_MAX = Decimal("10000000")
_CENTS = Decimal("0.01")


def collapse(raw: str) -> str | None:
    """Trim and collapse inner whitespace; blank becomes None. Case is never changed."""
    return " ".join(raw.split()) or None


def email(raw: str) -> str:
    value = raw.strip().lower()
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError:
        raise ValueError(f"email '{raw}' is not a valid address") from None
    return value


def region(raw: str) -> Region:
    key = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if key not in _REGION_KEYS:
        raise ValueError(f"region_code '{raw}' is not a known region")
    return _REGION_KEYS[key]


def status(raw: str) -> Status:
    try:
        return Status(raw.strip().lower())
    except ValueError:
        allowed = ", ".join(s.value for s in Status)
        raise ValueError(f"status '{raw}' is not one of: {allowed}") from None


def applied_date(raw: str) -> date | None:
    value = raw.strip()
    if not value:
        return None
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value):
        year, month, day = int(m[1]), int(m[2]), int(m[3])
    elif m := re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", value):
        month, day, year = int(m[1]), int(m[2]), int(m[3])
    elif (m := re.fullmatch(r"(\d{2})-([A-Za-z]{3})-(\d{4})", value)) and m[2].lower() in _MONTHS:
        day, month, year = int(m[1]), _MONTHS[m[2].lower()], int(m[3])
    else:
        raise ValueError(
            f"applied_date '{raw}' is not YYYY-MM-DD, MM/DD/YYYY or DD-Mon-YYYY")
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueError(f"applied_date '{raw}' is not a real calendar date") from None


def salary(raw: str) -> Decimal | None:
    value = re.sub(r"[$,\s]", "", raw)
    if not value or value.lower() in _SALARY_NULL_WORDS:
        return None
    multiplier = 1
    if value[-1] in "kK":
        value, multiplier = value[:-1], 1000
    if not re.fullmatch(r"-?\d+(\.\d+)?", value):
        raise ValueError(f"salary '{raw}' is not a number")
    amount = (Decimal(value) * multiplier).quantize(_CENTS, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValueError(f"salary '{raw}' must be greater than zero")
    if amount > _SALARY_MAX:
        raise ValueError(f"salary '{raw}' is above 10,000,000")
    return amount


def phone(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if not re.fullmatch(r"\+?[\d\s().-]+", value):
        raise ValueError(f"phone '{raw}' contains characters other than digits, spaces and ()-.+")
    digits = re.sub(r"\D", "", value)
    if not value.startswith("+"):
        if len(digits) != 10:
            raise ValueError(f"phone '{raw}' needs a +country code or exactly 10 digits")
        digits = "1" + digits
    if not 8 <= len(digits) <= 15:
        raise ValueError(f"phone '{raw}' must have 8 to 15 digits")
    return "+" + digits
