from __future__ import annotations

import json
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


###############################################################################
# CONFIG MODEL
###############################################################################

@dataclass(slots=True)
class Config:
    #
    # Trading Partner
    #

    sender_id: str
    receiver_id: str

    sender_tax_id: str

    #
    # Transaction
    #

    usage_indicator: str

    action_code: str

    purpose_code: str
    reference_id: str

    #
    # Output
    #

    output_directory: str

    #
    # Sponsor
    #

    sponsor_name: str
    sponsor_tax_id: str

    #
    # Payer
    #

    payer_name: str
    payer_identifier: str

    #
    # Other
    #

    group_number: str
    tier_structure: str
    time_zone_code: str


###############################################################################
# VALIDATION
###############################################################################

_VALID_USAGE_INDICATORS = {"P", "T"}

# Per companion guide (BGN08):
#   2 = Change/Update file / Full File with changes
#   4 = Verify/Audit
# NOTE: if action_code is ever "4", INS03 must be "030" and INS04 must be
# "XN" for every person (see models.py Person.maintenance_type), which is
# NOT currently implemented — that branch will need to be added before "4"
# is usable. For now this is validated but only "2" is actually supported
# end-to-end.
_VALID_ACTION_CODES = {"2", "4"}

# Fields that must be exactly 9 numeric digits (EIN / Tax ID format).
_NINE_DIGIT_FIELDS = ("sender_tax_id", "sponsor_tax_id", "payer_identifier")


def _validate_required_fields(data: dict[str, Any]) -> None:
    required = {field.name for field in fields(Config)}
    missing = required - data.keys()

    if missing:
        raise ValueError(
            f"Missing configuration fields: {sorted(missing)}"
        )


def _validate_field_values(data: dict[str, Any]) -> None:

    usage_indicator = data["usage_indicator"]
    if usage_indicator not in _VALID_USAGE_INDICATORS:
        raise ValueError(
            f"usage_indicator must be 'P' (production) or 'T' (test), "
            f"got {usage_indicator!r} in settings.json"
        )

    action_code = data["action_code"]
    if action_code not in _VALID_ACTION_CODES:
        raise ValueError(
            f"action_code must be '2' (full file) or '4' (audit/compare), "
            f"got {action_code!r} in settings.json"
        )

    for field_name in _NINE_DIGIT_FIELDS:
        value = data[field_name]
        if not (isinstance(value, str) and value.isdigit() and len(value) == 9):
            raise ValueError(
                f"{field_name} must be exactly 9 digits, "
                f"got {value!r} in settings.json"
            )


def _apply_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """
    Fill in values the user shouldn't need to think about every week.

    reference_id (BGN02) in particular should NOT be hand-maintained in
    settings.json long-term -- it's meant to uniquely identify each
    occurrence of the transaction, and a static value re-used every week
    defeats that purpose. If left blank, we generate a timestamp-based one.
    Once control_numbers.py is wired in, this should likely move there
    instead so it's tracked alongside ISA13/GS06/ST02.
    """

    if not data.get("reference_id"):
        data["reference_id"] = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    return data


###############################################################################
# LOADER
###############################################################################

def load_config(
    filename: str | Path = "settings.json",
) -> Config:

    path = Path(filename)

    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as fp:

        data: dict[str, Any] = json.load(fp)

    _validate_required_fields(data)

    data = _apply_defaults(data)

    _validate_field_values(data)

    #
    # Resolve output_directory relative to settings.json's own location,
    # not the process's current working directory. This matters if the
    # tool is ever launched by double-click or a scheduled task, where
    # the working directory isn't guaranteed to be the project folder.
    #
    output_dir = Path(data["output_directory"])
    if not output_dir.is_absolute():
        output_dir = (path.resolve().parent / output_dir).resolve()
    data["output_directory"] = str(output_dir)

    return Config(**data)