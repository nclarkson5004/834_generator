from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Iterable

from x12_constants import (
    COUNTRY_CODES,
    COUNTRY_NAME_TO_CODE,
    DATE_FORMATS,
    DEFAULT_COUNTRY,
    FALSE_VALUES,
    TRUE_VALUES,
)

logger = logging.getLogger(__name__)

###############################################################################
# Strings
###############################################################################


def clean(value: object | None) -> str:
    """
    Converts None to an empty string and strips whitespace.
    """

    if value is None:
        return ""

    return str(value).strip()


def upper(value: object | None) -> str:
    """
    Returns a cleaned uppercase string.
    """

    return clean(value).upper()


def truncate(
    value: object | None,
    length: int,
) -> str:

    return clean(value)[:length]


###############################################################################
# EDI Text
###############################################################################


# Includes the repetition separator (^) alongside the element separator,
# segment terminator, and subelement separator -- all four are reserved
# delimiters per x12_constants.py and none belong in free-text fields.
_ILLEGAL_EDI = re.compile(r"[*~:^]")

_MULTIPLE_SPACES = re.compile(r"\s+")


def sanitize_edi(value: object | None) -> str:
    """
    Removes illegal EDI delimiter characters and normalizes whitespace.
    """

    text = clean(value)

    text = _ILLEGAL_EDI.sub(" ", text)

    text = _MULTIPLE_SPACES.sub(" ", text)

    return text.strip()

def edi_string(
    value: object | None,
    length: int | None = None,
) -> str:

    text = sanitize_edi(value)

    if length is not None:
        text = text[:length]

    return text


###############################################################################
# Dates
###############################################################################


def parse_date(value: str) -> datetime | None:
    """
    Attempts to parse a supported date format.
    """

    value = clean(value)

    if not value:
        return None

    for fmt in DATE_FORMATS:

        try:
            return datetime.strptime(value, fmt)

        except ValueError:
            pass

    return None


def edi_date(value: str) -> str:
    """
    Converts a date into CCYYMMDD. Logs a warning (rather than failing
    silently) when a non-blank value couldn't be parsed against any known
    format, since a REQUIRED DTP segment silently going out blank is a
    likely source of downstream rejections.
    """

    dt = parse_date(value)

    if dt is None:
        if clean(value):
            logger.warning(
                "Could not parse date %r against known formats %s",
                value,
                DATE_FORMATS,
            )
        return ""

    return dt.strftime("%Y%m%d")


def _now() -> datetime:
    """
    Single shared 'now' so a caller building both ISA and GS timestamps in
    the same envelope can request one consistent snapshot rather than two
    independent datetime.now() calls that could (rarely) straddle midnight.
    """

    return datetime.now()


def isa_date(now: datetime | None = None) -> str:
    """
    ISA date (YYMMDD). Pass a shared `now` if calling alongside isa_time()/
    gs_date()/gs_time() for the same envelope.
    """

    return (now or _now()).strftime("%y%m%d")


def isa_time(now: datetime | None = None) -> str:
    """
    ISA time (HHMM).
    """

    return (now or _now()).strftime("%H%M")


def gs_date(now: datetime | None = None) -> str:
    """
    GS date (CCYYMMDD).
    """

    return (now or _now()).strftime("%Y%m%d")


def gs_time(now: datetime | None = None) -> str:
    """
    GS time (HHMM).
    """

    return (now or _now()).strftime("%H%M")


###############################################################################
# Numbers
###############################################################################


def digits(value: object | None) -> str:
    """
    Returns only numeric digits.
    """

    return "".join(c for c in clean(value) if c.isdigit())


def normalize_ssn(value: object | None) -> str:
    """
    Strips to digits only. Warns if the result isn't 9 digits, since a
    common failure mode is a source spreadsheet storing SSN as a number
    and silently dropping a leading zero.
    """

    result = digits(value)

    if result and len(result) != 9:
        logger.warning(
            "SSN %r normalized to %d digits, expected 9 -- "
            "possible leading-zero loss from a numeric-typed source column",
            value,
            len(result),
        )

    return result


def normalize_phone(value: object | None) -> str:

    return digits(value)


def normalize_zip(value: object | None) -> str:
    """
    Strips to digits only. Warns if the result isn't 5 or 9 digits, for
    the same leading-zero-loss reason as normalize_ssn.
    """

    result = digits(value)

    if result and len(result) not in (5, 9):
        logger.warning(
            "ZIP %r normalized to %d digits, expected 5 or 9 -- "
            "possible leading-zero loss from a numeric-typed source column",
            value,
            len(result),
        )

    return result


###############################################################################
# Country
###############################################################################


def normalize_country(value: object | None) -> str:
    """
    Normalizes a country column into a 2-letter code. Accepts either an
    already-valid code (e.g. "US") or a full country name (e.g.
    "United States") as it might appear in an HR export, looking the
    latter up against x12_constants.COUNTRY_CODES rather than blindly
    truncating to 2 characters (which previously mangled names like
    "Mexico" -> "ME" instead of "MX").
    """

    country = upper(value)

    if not country:
        return DEFAULT_COUNTRY

    if country in COUNTRY_CODES:
        return country

    if country in COUNTRY_NAME_TO_CODE:
        return COUNTRY_NAME_TO_CODE[country]

    logger.warning(
        "Unrecognized country %r, defaulting to %s",
        value,
        DEFAULT_COUNTRY,
    )

    return DEFAULT_COUNTRY


###############################################################################
# Boolean
###############################################################################


def to_bool(value: object | None) -> bool:
    """
    Warns when a non-blank value doesn't match a known true/false token,
    since silently defaulting an unrecognized tobacco-user/disabled flag
    to False can have real cost implications if it's actually bad data
    rather than a genuine "No".
    """

    normalized = upper(value)

    if normalized in TRUE_VALUES:
        return True

    if normalized in FALSE_VALUES:
        return False

    if normalized:
        logger.warning(
            "Unrecognized boolean value %r, defaulting to False",
            value,
        )

    return False


###############################################################################
# Lists
###############################################################################


def unique(values: Iterable[str]) -> list[str]:
    """
    Preserves order while removing duplicates.
    """

    seen = set()

    result = []

    for value in values:

        if value not in seen:

            seen.add(value)

            result.append(value)

    return result


###############################################################################
# Control Numbers
###############################################################################


def zero_fill(number: int, width: int) -> str:
    """
    Pads a control number with leading zeroes.
    """

    return str(number).zfill(width)