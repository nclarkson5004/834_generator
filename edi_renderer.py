from __future__ import annotations

from edi_writer import X12Writer
from models import Coverage, Person, Subscriber
from utils import edi_date
from x12_constants import get_tier_code


# =============================================================================
# PUBLIC ENTRY POINT
#
# The 834 transaction does NOT use HL segments -- subscriber/dependent
# grouping is expressed purely by INS01 (Y/N) and physical ordering (a
# dependent's loop 2000 immediately follows its subscriber's), confirmed
# against the companion guide's full segment layout (no HL entry exists
# anywhere in it) and multiple real-world 834 samples. hl_tree.py /
# hl_validator.py are no longer needed -- Subscriber.employee /
# Subscriber.dependents already give the correct grouping and order.
# =============================================================================


def render_members(
    writer: X12Writer,
    subscribers: list[Subscriber],
    *,
    tier_structure: str,
    group_number: str,
) -> None:
    """
    Emits loop 2000 (INS + REF) and nested loop 2100/2300 for every
    subscriber, immediately followed by each of their dependents.

    tier_structure: one of "2_TIER"/"3_TIER"/"4_TIER" -- see
        x12_constants.get_tier_code(). This is presumed to be a
        per-plan/per-group setting; wire it in from config once that's
        settled.
    group_number: REF*1L* value at the member (2000) level -- source
        TBD, see TODO in _write_member_ref.
    """

    for subscriber in subscribers:

        _render_member(
            writer,
            subscriber=subscriber,
            person=subscriber.employee,
            tier_structure=tier_structure,
            group_number=group_number,
        )

        for dependent in subscriber.dependents:
            _render_member(
                writer,
                subscriber=subscriber,
                person=dependent,
                tier_structure=tier_structure,
                group_number=group_number,
            )


# =============================================================================
# MEMBER LOOP (2000 + 2100 + 2300)
# =============================================================================


def _render_member(
    writer: X12Writer,
    subscriber: Subscriber,
    person: Person,
    tier_structure: str,
    group_number: str,
) -> None:

    _write_ins(writer, subscriber, person)
    _write_member_ref(writer, person, group_number)

    _render_2100(writer, person)
    _render_2300(writer, person, tier_structure)


# =============================================================================
# 2000 INS
#
# FIX: previous version had an extra blank element, shifting INS09
# (student status) and INS10 (handicap indicator) one slot to the right
# into INS10/INS11. Also now populates INS08 (Employment Status Code),
# previously always blank -- guide's own example shows "AC" (Active);
# valid values also include FT, PT, L1 (Leave), TE (Terminated), RT
# (Retired), per the guide's INS08 code list.
# =============================================================================


def _write_ins(
    writer: X12Writer,
    subscriber: Subscriber,
    person: Person,
) -> None:

    writer.segment(
        "INS",
        person.member_indicator,      # INS01
        person.relationship_value,    # INS02
        person.maintenance_type,      # INS03
        person.maintenance_reason,    # INS04
        "A",                          # INS05 - Benefit Status (guide: send A other than COBRA/survivor)
        "",                           # INS06 - Medicare Status (situational, not modeled yet)
        "",                           # INS07 - COBRA Qualifying Event (situational)
        _employment_status_code(subscriber),  # INS08
        person.student_status,        # INS09
        person.disabled,              # INS10
    )


def _employment_status_code(subscriber: Subscriber) -> str:
    """
    Maps Subscriber.employee_status to the guide's INS08 code list.
    TODO: confirm this mapping against actual values appearing in your
    census's "Employee Status" column -- filled in with a best guess
    based on common HRIS status strings; adjust as needed.
    """

    status = (subscriber.employee_status or "").strip().upper()

    return {
        "ACTIVE": "AC",
        "FULL-TIME": "FT",
        "FULL TIME": "FT",
        "PART-TIME": "PT",
        "PART TIME": "PT",
        "LEAVE OF ABSENCE": "L1",
        "LEAVE": "L1",
        "TERMINATED": "TE",
        "RETIRED": "RT",
    }.get(status, "AC")


# =============================================================================
# 2000 REF (Subscriber Identifier + Member Policy Number)
# =============================================================================


def _write_member_ref(
    writer: X12Writer,
    person: Person,
    group_number: str,
) -> None:

    # REF*0F* - Subscriber Identifier. Guide: "Must be sent for each
    # record" -- i.e. required for both subscriber and every dependent,
    # carrying the same family-level identifier. Confirmed correct as-is.
    if person.member_id:
        writer.segment("REF", "0F", person.member_id)

    # REF*1L* - Member Policy Number / Group Number. REQUIRED per guide,
    # but not currently modeled anywhere (Config, Subscriber, Coverage).
    # TODO: confirm where this should come from before shipping -- a new
    # settings.json field? Derived from Coverage.policy_number? Left
    # guarded so it's simply omitted (not fabricated) until resolved.
    if group_number:
        writer.segment("REF", "1L", group_number)

    # REF*DX* - Member Supplemental Identifier (EE Location Code).
    # REQUIRED per guide ("see account structure"), but no field in
    # Subscriber currently models a location code distinct from
    # department/division/job_title.
    # TODO: this segment is NOT currently emitted. Needs a data source
    # before it can be added -- confirm with your trading partner /
    # account structure docs what this value should be.


# =============================================================================
# 2100 LOOP
# =============================================================================


def _render_2100(
    writer: X12Writer,
    person: Person,
) -> None:

    _write_nm1(writer, person)
    _write_per(writer, person)
    _write_n3(writer, person)
    _write_n4(writer, person)
    _write_dmg(writer, person)


def _write_nm1(
    writer: X12Writer,
    person: Person,
) -> None:
    """
    FIX: NM108/NM109 (SSN qualifier/value) are now conditional on the
    person actually having an SSN. Guide: "If dependent SSN is not
    available, do not send 34 in NM108."
    """

    has_ssn = bool(person.ssn)

    writer.segment(
        "NM1",
        "IL",
        "1",
        person.last_name,
        person.first_name,
        person.middle_name,
        "",
        "",
        "34" if has_ssn else "",
        person.ssn if has_ssn else "",
    )


def _write_per(
    writer: X12Writer,
    person: Person,
) -> None:
    """
    FIX: combined into a single PER segment (phone in slot 1, email in
    slot 2) matching the guide's own example, instead of two separate
    PER segments. Also picks the qualifier matching whichever phone
    field was actually used, rather than hardcoding "TE".
    """

    phone, phone_qualifier = _best_phone(person)

    if not phone and not person.email:
        return

    writer.segment(
        "PER",
        "IP",
        "",
        phone_qualifier if phone else "",
        phone,
        "EM" if person.email else "",
        person.email,
    )


def _best_phone(person: Person) -> tuple[str, str]:

    if person.mobile_phone:
        return person.mobile_phone, "CP"

    if person.home_phone:
        return person.home_phone, "HP"

    if person.work_phone:
        return person.work_phone, "WP"

    return "", ""


def _write_n3(
    writer: X12Writer,
    person: Person,
) -> None:

    writer.segment(
        "N3",
        person.address1,
        person.address2,
    )


def _write_n4(
    writer: X12Writer,
    person: Person,
) -> None:

    writer.segment(
        "N4",
        person.city,
        person.state,
        person.zip_code,
        person.country,
    )


def _write_dmg(
    writer: X12Writer,
    person: Person,
) -> None:
    """
    FIX: birth_date is now run through utils.edi_date() to produce
    proper D8 (CCYYMMDD) format instead of the raw census string.
    """

    writer.segment(
        "DMG",
        "D8",
        edi_date(person.birth_date),
        person.normalized_gender,
        person.normalized_marital_status,
    )


# =============================================================================
# 2300 COVERAGE LOOP
# =============================================================================


def _render_2300(
    writer: X12Writer,
    person: Person,
    tier_structure: str,
) -> None:

    for coverage in person.coverages:

        _write_hd(writer, coverage, tier_structure)
        _write_coverage_ref(writer, coverage)
        _write_dtp(writer, coverage)


def _write_hd(
    writer: X12Writer,
    coverage: Coverage,
    tier_structure: str,
) -> None:
    """
    FIX: HD05 (Coverage Level Code) is now resolved through
    x12_constants.get_tier_code() instead of sending the raw census
    string. Confirmed against the guide's own example
    ("HD*030**HLT**FAM~") that tier code belongs at HD05, matching what
    x12_constants.py already assumes.
    """

    tier_code = get_tier_code(coverage.coverage_tier, tier_structure)

    writer.segment(
        "HD",
        coverage.maintenance_type,   # HD01
        "",                          # HD02 - Maintenance Reason (NOT USED per guide)
        coverage.insurance_line_code,  # HD03
        "",                          # HD04 - Plan Coverage Description (guide: "Not required")
        tier_code,                   # HD05
    )


def _write_coverage_ref(
    writer: X12Writer,
    coverage: Coverage,
) -> None:
    """
    REF*1L* at the 2300 (coverage) level -- Plan/Contract Number & Class
    Code, REQUIRED per guide. Distinct from the 2000-level REF*1L*
    (group number) above -- same qualifier, different loop, different
    meaning.

    TODO: guide's notes suggest the value may need to be a concatenation
    of policy number (first 12 chars) + a 3-character class code, but
    the exact source of "class code" isn't clear from the guide excerpt
    alone -- confirm with the trading partner before relying on this.
    For now this sends policy_number alone.
    """

    if coverage.policy_number:
        writer.segment("REF", "1L", coverage.policy_number)


def _write_dtp(
    writer: X12Writer,
    coverage: Coverage,
) -> None:
    """
    FIX: effective_date/end_date now run through utils.edi_date() to
    produce D8 (CCYYMMDD) format instead of the raw census string.
    """

    effective = edi_date(coverage.effective_date)
    end = edi_date(coverage.end_date)

    if effective:
        writer.segment("DTP", "348", "D8", effective)

    if end:
        writer.segment("DTP", "349", "D8", end)