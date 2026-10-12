from __future__ import annotations

from config import Config
from edi_writer import X12Writer
from utils import gs_date, gs_time


# Per companion guide BGN05: valid time zone codes are CT (Central),
# ES (Eastern Standard), PS (Pacific Standard), MT (Mountain) -- no
# other zones are listed as valid.
_VALID_TIME_CODES = {"CT", "ES", "PS", "MT"}


# =============================================================================
# BGN - BEGINNING SEGMENT
# =============================================================================

def write_bgn(
    writer: X12Writer,
    config: Config,
) -> None:

    if config.time_zone_code not in _VALID_TIME_CODES:
        raise ValueError(
            f"time_zone_code must be one of {sorted(_VALID_TIME_CODES)}, "
            f"got {config.time_zone_code!r}"
        )

    writer.segment(
        "BGN",
        config.purpose_code,     # BGN01 - Transaction Set Purpose Code
        config.reference_id,     # BGN02 - Reference Identification
        gs_date(),                # BGN03 - Date (CCYYMMDD)
        gs_time(),                # BGN04 - Time (HHMM)
        config.time_zone_code,   # BGN05 - Time Code
        "",                       # BGN06 - Situational (original ref #, not used for full files)
        "",                       # BGN07 - NOT USED
        config.action_code,      # BGN08 - Action Code (2 = full file, 4 = audit)
        "",                       # BGN09 - NOT USED
    )


# =============================================================================
# REF*38* - TRANSACTION SET POLICY NUMBER (GROUP NUMBER)
# =============================================================================

def write_group_number_ref(
    writer: X12Writer,
    config: Config,
) -> None:
    """
    SITUATIONAL segment overall, but REF01/REF02 are REQUIRED when it's
    sent. Uses the same group_number value that hl_to_edi_renderer.py's
    2000-level REF*1L* references -- make sure that's filled in in
    settings.json once you've confirmed where it comes from.
    """

    if not config.group_number:
        return

    writer.segment(
        "REF",
        "38",
        config.group_number,
    )


# =============================================================================
# ORCHESTRATION
# =============================================================================

def write_transaction_header(
    writer: X12Writer,
    config: Config,
) -> None:

    write_bgn(writer, config)
    write_group_number_ref(writer, config)