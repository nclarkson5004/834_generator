from __future__ import annotations

from models import Coverage, Person, Subscriber
from utils import parse_date


# =============================================================================
# EXCEPTION
# =============================================================================

class EDI834ValidationError(Exception):
    """
    Raised with every validation problem found across the whole file,
    not just the first one -- see validate_834.
    """
    pass


# =============================================================================
# PUBLIC ENTRY
# =============================================================================

def validate_834(subscribers: list[Subscriber]) -> None:
    """
    Validates 834 semantic correctness AFTER the member loops are built.

    This is NOT a structural validator (envelope/ISA/GS/ST-level).
    This is a business-rule / EDI-rule validator.

    Collects every problem found across all subscribers and raises them
    together in one EDI834ValidationError, rather than stopping at the
    first one -- so a single run surfaces everything that needs fixing.
    """

    if not subscribers:
        raise EDI834ValidationError("No subscribers provided")

    errors: list[str] = []

    for subscriber in subscribers:
        errors.extend(_validate_subscriber(subscriber))

    if errors:
        raise EDI834ValidationError(
            f"{len(errors)} validation error(s) found:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# =============================================================================
# SUBSCRIBER LEVEL
# =============================================================================

def _validate_subscriber(subscriber: Subscriber) -> list[str]:

    errors: list[str] = []

    try:
        employee = subscriber.employee

    except ValueError as exc:
        # Subscriber.employee raises rather than returning something
        # falsy, so this can't be caught with a plain `if not ...:` --
        # it has to be wrapped.
        errors.append(f"Subscriber {subscriber.subscriber_key}: {exc}")
        return errors

    errors.extend(_validate_person(employee, is_employee=True))

    for dep in subscriber.dependents:
        errors.extend(_validate_person(dep, is_employee=False))

    return errors


# =============================================================================
# PERSON LEVEL (2000 + 2100 RULES)
# =============================================================================

def _validate_person(person: Person, is_employee: bool) -> list[str]:

    errors: list[str] = []

    # ---------------------------------------------------------
    # REQUIRED CORE FIELDS
    # ---------------------------------------------------------

    if not person.first_name or not person.last_name:
        errors.append(f"Person missing required name fields: {person}")

    if not person.birth_date:
        errors.append(f"Person {person.full_name} missing birth_date")

    if not person.gender:
        errors.append(f"Person {person.full_name} missing gender")

    if not person.address1:
        errors.append(f"Person {person.full_name} missing address1")

    if not person.city or not person.state or not person.zip_code:
        errors.append(f"Person {person.full_name} missing city/state/zip")

    # ---------------------------------------------------------
    # INS RULES
    # ---------------------------------------------------------

    if is_employee and person.member_indicator != "Y":
        errors.append(f"Employee must have INS01 = 'Y': {person.full_name}")

    if not is_employee and person.member_indicator != "N":
        errors.append(f"Dependent must have INS01 = 'N': {person.full_name}")

    if not person.relationship_value:
        errors.append(f"Missing relationship code for {person.full_name}")

    # ---------------------------------------------------------
    # COVERAGE RULES (2300 LOOP)
    # ---------------------------------------------------------

    if not person.coverages:
        # A person with zero coverage rows at all didn't come through
        # any plan row in the census -- distinct from a person whose
        # only row is an explicit waiver (that's a populated Coverage
        # with is_waived=True, not an empty list).
        errors.append(
            f"Person {person.full_name} has no coverage records at all"
        )

    for cov in person.coverages:
        errors.extend(_validate_coverage(cov, person))

    return errors


# =============================================================================
# COVERAGE LEVEL (2300 LOOP)
# =============================================================================

def _validate_coverage(coverage: Coverage, person: Person) -> list[str]:

    errors: list[str] = []

    if not coverage.plan_type:
        errors.append(f"{person.full_name} has coverage missing plan_type")

    if not coverage.insurance_line_code:
        errors.append(f"{person.full_name} has invalid insurance_line_code")

    if not coverage.maintenance_type:
        errors.append(f"{person.full_name} has missing maintenance_type")

    # ---------------------------------------------------------
    # DTP RULES
    #
    # FIX: dates are compared as parsed datetimes now, not raw strings
    # -- string comparison on MM/DD/YYYY-style input doesn't sort
    # chronologically (e.g. "02/01/2025" < "01/15/2026" as strings,
    # which is backwards).
    # ---------------------------------------------------------

    if not coverage.effective_date:
        errors.append(f"{person.full_name} coverage missing effective_date")

    else:
        effective = parse_date(coverage.effective_date)

        if effective is None:
            errors.append(
                f"{person.full_name} coverage has an unparseable "
                f"effective_date: {coverage.effective_date!r}"
            )

        elif coverage.end_date:
            end = parse_date(coverage.end_date)

            if end is None:
                errors.append(
                    f"{person.full_name} coverage has an unparseable "
                    f"end_date: {coverage.end_date!r}"
                )

            elif end < effective:
                errors.append(
                    f"{person.full_name} coverage end_date "
                    f"({coverage.end_date}) is before effective_date "
                    f"({coverage.effective_date})"
                )

    # ---------------------------------------------------------
    # WAIVED COVERAGE RULE
    #
    # REMOVED: the previous rule ("waived coverage must be ADD/021")
    # doesn't trace back to anything in the companion guide, and reads
    # backwards on its face -- a coverage going from active to waived
    # this cycle would more naturally be a Terminate (024) or Change
    # (001), not an Add (021). Left out rather than kept on an
    # unconfirmed assumption. If there's a specific rule your trading
    # partner gave you here, let's rebuild it correctly against that.
    #
    # Also fixed: was comparing coverage.election_status == "WAIVED"
    # directly (a raw, un-normalized CSV string) instead of using
    # coverage.is_waived, which already does this comparison correctly.
    # ---------------------------------------------------------

    return errors