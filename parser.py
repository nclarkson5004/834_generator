import csv
import logging
import re
from pathlib import Path

from models import Coverage, Person, Subscriber
from utils import clean

logger = logging.getLogger(__name__)


# =============================================================================
# REQUIRED CSV SCHEMA
# =============================================================================

REQUIRED_COLUMNS = {
    "Subscriber Key",
    "Relationship",
    "Relationship Code",
    "First Name",
    "Last Name",
    "SSN",
    "Birth Date",
    "Sex",
    "Address 1",
    "City",
    "State",
    "Zip",
    "Company Name",
    "EID",
    "Employee Status",
    "Employee Type",
    "Hire Date",
    "Plan Type",
    "Plan Display Name",
    "Carrier",

    "Policy Number",
    "Subgroup Number",
    "Coverage Tier",
    "Plan Effective Start Date",
    "Plan Effective End Date",
    "Election Status",
    "Action",
    "Employee Contribution",
    "Employer Contribution",
    "Employee Cost Per Deduction Period",
}


# =============================================================================
# NORMALIZATION HELPERS
# =============================================================================

def value(row: dict[str, str], column: str) -> str:
    return clean(row.get(column) or "")


def normalize_ssn(ssn: str) -> str:
    digits = "".join(c for c in ssn if c.isdigit())

    if digits and len(digits) != 9:
        logger.warning(
            "SSN %r normalized to %d digits, expected 9 -- "
            "possible leading-zero loss from a numeric-typed source column",
            ssn,
            len(digits),
        )

    return digits


def normalize_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())


def normalize_zip(zip_code: str) -> str:
    digits = "".join(c for c in zip_code if c.isdigit())

    if digits and len(digits) not in (5, 9):
        logger.warning(
            "ZIP %r normalized to %d digits, expected 5 or 9 -- "
            "possible leading-zero loss from a numeric-typed source column",
            zip_code,
            len(digits),
        )

    return digits


def normalize_key(value: str) -> str:
    return clean(value or "").lower()


# =============================================================================
# SUBSCRIBER KEY HANDLING
#
# Confirmed: the "Subscriber Key" column carries a per-PERSON suffix, not
# a per-FAMILY one -- the employee's rows have no suffix at all (e.g.
# "3k99ep"), while each dependent's rows carry their own trailing
# "-<number>" (e.g. "3k99ep-1" for the first dependent, "3k99ep-2" for
# the second, etc.).
#
# Grouping by the raw, unstripped value (the previous behavior) splits
# every family into N+1 unrelated "subscribers" -- one per dependent,
# each missing an employee entirely, plus one employee-only group
# missing all its dependents. The FAMILY grouping key needs the suffix
# stripped; the PERSON-level key needs to keep it, since it's exactly
# what distinguishes one dependent from another when SSN is blank.
# =============================================================================

_SUFFIX_PATTERN = re.compile(r"-\d+$")


def family_key(row: dict[str, str]) -> str:
    """
    The true family-grouping key: the raw Subscriber Key with any
    trailing "-<number>" dependent suffix stripped off.
    """

    raw = value(row, "Subscriber Key")

    return normalize_key(_SUFFIX_PATTERN.sub("", raw))


def raw_subscriber_key(row: dict[str, str]) -> str:
    """
    The unstripped Subscriber Key, including any dependent suffix.
    Used for per-person identity, NOT for family grouping.
    """

    return normalize_key(value(row, "Subscriber Key"))


# =============================================================================
# KEY BUILDERS
# =============================================================================

def build_person_key(row: dict[str, str]) -> str:
    """
    The raw Subscriber Key encodes RELATIONSHIP TYPE, not a unique
    person index -- "-0" = employee, "-1" = spouse, "-2" = child, but
    multiple children all share the same "-2" suffix. So the raw key
    alone can't distinguish one child from another; SSN can't either,
    since it's sometimes blank or shares a placeholder value inherited
    from the employee (e.g. spouse rows).

    Instead, combine the raw key (which still correctly separates
    employee/spouse/child from each other) with name + birth date,
    which reliably distinguishes multiple children under the same
    relationship code from one another.
    """
    return "|".join([
        raw_subscriber_key(row),
        normalize_key(value(row, "First Name")),
        normalize_key(value(row, "Last Name")),
        normalize_key(value(row, "Birth Date")),
    ])


def build_coverage_key(row: dict[str, str]) -> str:
    return "|".join([
        normalize_key(value(row, "Plan Type")),
        normalize_key(value(row, "Policy Number")),
        normalize_key(value(row, "Subgroup Number")),
        normalize_key(value(row, "Plan Effective Start Date")),
        normalize_key(value(row, "Plan Effective End Date")),
        normalize_key(value(row, "Coverage Tier")),
    ])


# =============================================================================
# MAIN ENTRY
# =============================================================================

def read_census(csv_file: str | Path) -> list[Subscriber]:

    csv_file = Path(csv_file)

    if not csv_file.exists():
        raise FileNotFoundError(csv_file)

    subscribers: dict[str, Subscriber] = {}

    # 👇 IMPORTANT: dedup state lives HERE, not in Person
    coverage_seen: dict[tuple[str, str], set[str]] = {}

    with csv_file.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)

        if not reader.fieldnames:
            raise ValueError("CSV contains no header row.")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                "CSV is missing required columns:\n"
                + "\n".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                parse_row(row, subscribers, coverage_seen)

            except Exception as exc:
                raise ValueError(
                    f"Error parsing CSV line {line_number}: {exc}"
                ) from exc

    result = list(subscribers.values())

    _backfill_dependent_addresses(result)

    logger.info("Loaded %d subscribers", len(result))
    return result


# =============================================================================
# ADDRESS BACKFILL
#
# N3/N4 (address) are REQUIRED per companion guide for every member
# record, including dependents -- but dependents living at the same
# address as the employee are commonly left blank in census exports.
# Rather than relax validation, fill in the employee's own address for
# any dependent missing theirs.
# =============================================================================

def _backfill_dependent_addresses(subscribers: list[Subscriber]) -> None:

    for subscriber in subscribers:

        try:
            employee = subscriber.employee
        except ValueError:
            # Missing/duplicate employee is a real problem, but it's
            # not this function's job to report it -- edi_834_validator
            # will catch it.
            continue

        for dependent in subscriber.dependents:

            if not dependent.address1:
                dependent.address1 = employee.address1
                dependent.address2 = employee.address2
                dependent.city = employee.city
                dependent.state = employee.state
                dependent.zip_code = employee.zip_code
                dependent.county = employee.county
                dependent.country = employee.country

                logger.debug(
                    "Backfilled address for dependent %s from employee "
                    "in subscriber %s",
                    dependent.full_name,
                    subscriber.subscriber_key,
                )


# =============================================================================
# ROW PARSER
# =============================================================================

def parse_row(
    row: dict[str, str],
    subscribers: dict[str, Subscriber],
    coverage_seen: dict[tuple[str, str], set[str]],
) -> None:

    subscriber_key = family_key(row)

    if not subscriber_key:
        logger.warning("Skipping row missing Subscriber Key")
        return

    # -------------------------------------------------------------
    # SUBSCRIBER
    # -------------------------------------------------------------

    subscriber = subscribers.get(subscriber_key)

    if subscriber is None:
        subscriber = Subscriber(
            subscriber_key=subscriber_key,
            company_name=value(row, "Company Name"),
            employee_id=value(row, "EID"),
            employee_status=value(row, "Employee Status"),
            employee_type=value(row, "Employee Type"),
            hire_date=value(row, "Hire Date"),
            termination_date=value(row, "Termination Date"),
            termination_type=value(row, "Termination Type"),
            department=value(row, "Department"),
            division=value(row, "Division"),
            job_title=value(row, "Job Title"),
            benefit_eligible_date=value(row, "Benefit Eligible Date"),
        )
        subscribers[subscriber_key] = subscriber

    # -------------------------------------------------------------
    # PERSON
    # -------------------------------------------------------------

    person_key = build_person_key(row)
    person = subscriber.get_person(person_key)

    if person is None:
        person = build_person(row, subscriber_key)
        subscriber.add_person(person_key, person)

    # -------------------------------------------------------------
    # COVERAGE (GLOBAL DEDUP PER PERSON)
    # -------------------------------------------------------------

    coverage_key = build_coverage_key(row)

    person_cov_key = (subscriber_key, person_key)

    if person_cov_key not in coverage_seen:
        coverage_seen[person_cov_key] = set()

    if coverage_key in coverage_seen[person_cov_key]:
        logger.warning(
            "Skipping duplicate coverage subscriber=%s person=%s plan=%s",
            subscriber_key,
            person_key,
            value(row, "Plan Type"),
        )
        return

    coverage_seen[person_cov_key].add(coverage_key)
    person.add_coverage(build_coverage(row))


# =============================================================================
# PERSON BUILDER
# =============================================================================

def build_person(row: dict[str, str], subscriber_key: str) -> Person:
    """
    subscriber_key here is the FAMILY key (suffix stripped) -- used for
    member_id so that REF*0F* carries the same shared family identifier
    for the employee and every dependent, matching the guide's example
    of REF*0F* repeating the same value across a family's records.
    """
    return Person(
        relationship=value(row, "Relationship"),
        relationship_code=value(row, "Relationship Code"),

        first_name=value(row, "First Name"),
        middle_name=value(row, "Middle Name"),
        last_name=value(row, "Last Name"),

        member_id=subscriber_key,
        ssn=normalize_ssn(value(row, "SSN")),

        gender=value(row, "Sex"),
        birth_date=value(row, "Birth Date"),

        address1=value(row, "Address 1"),
        address2=value(row, "Address 2"),

        city=value(row, "City"),
        state=value(row, "State"),
        zip_code=normalize_zip(value(row, "Zip")),

        county=value(row, "County"),
        country=value(row, "Country"),

        email=value(row, "Email"),

        home_phone=normalize_phone(value(row, "Personal Phone")),
        mobile_phone=normalize_phone(value(row, "Mobile Phone")),
        work_phone=normalize_phone(value(row, "Work Phone")),

        marital_status=value(row, "Marital Status"),

        disabled=value(row, "Disabled"),
        tobacco_user=value(row, "Tobacco User"),

        medicare_a_date=value(row, "Medicare A Date"),
        medicare_b_date=value(row, "Medicare B Date"),
        medicare_c_date=value(row, "Medicare C Date"),
        medicare_d_date=value(row, "Medicare D Date"),
    )


# =============================================================================
# COVERAGE BUILDER
# =============================================================================

def build_coverage(row: dict[str, str]) -> Coverage:
    return Coverage(
        plan_type=value(row, "Plan Type"),
        plan_name=value(row, "Plan Display Name"),
        carrier=value(row, "Carrier"),

        policy_number=value(row, "Policy Number"),
        subgroup_number=value(row, "Subgroup Number"),

        coverage_tier=value(row, "Coverage Tier"),

        effective_date=value(row, "Plan Effective Start Date"),
        end_date=value(row, "Plan Effective End Date"),

        election_status=value(row, "Election Status"),
        action=value(row, "Action"),

        employee_contribution=value(row, "Employee Contribution"),
        employer_contribution=value(row, "Employer Contribution"),
        employee_cost=value(row, "Employee Cost Per Deduction Period"),
    )