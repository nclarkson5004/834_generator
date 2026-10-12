from control_numbers import ControlNumbers
from edi_writer import X12Writer


# =============================================================================
# SE - TRANSACTION SET TRAILER
# =============================================================================

def write_se(
    writer: X12Writer,
    control: ControlNumbers,
) -> None:

    if not writer.transaction_started:
        raise RuntimeError("Cannot write SE without starting transaction (ST missing)")

    segment_count = writer.transaction_segment_count()

    writer.segment(
        "SE",
        str(segment_count),
        control.st_control_number,
    )


# =============================================================================
# GE - FUNCTIONAL GROUP TRAILER
# =============================================================================

def write_ge(
    writer: X12Writer,
    control: ControlNumbers,
) -> None:

    # Currently assumes single transaction per group
    # but made explicit for future scaling

    writer.segment(
        "GE",
        "1",
        control.gs_control_number,
    )


# =============================================================================
# IEA - INTERCHANGE TRAILER
# =============================================================================

def write_iea(
    writer: X12Writer,
    control: ControlNumbers,
) -> None:

    # Currently assumes single functional group per interchange

    writer.segment(
        "IEA",
        "1",
        control.isa_control_number,
    )


# =============================================================================
# ORCHESTRATION
# =============================================================================

def write_trailer(
    writer: X12Writer,
    control: ControlNumbers,
) -> None:

    write_se(writer, control)
    write_ge(writer, control)
    write_iea(writer, control)