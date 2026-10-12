from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "control_numbers.json"

# ISA13 is a fixed 9-digit field; ST02 must be at least 4 characters per
# the companion guide ("minimum length is 4bytes long"). GS06 has no
# documented minimum, so it's left as a plain (unpadded) integer string.
_ISA13_WIDTH = 9
_ST02_MIN_WIDTH = 4
_ISA13_MAX = 10 ** _ISA13_WIDTH - 1


@dataclass(slots=True)
class ControlNumbers:
    """
    Maintains the X12 interchange control number.

    A single control number is used for ISA13, GS06, and ST02. This
    assumes exactly one ISA / one GS / one ST per generated file -- if
    that ever changes (e.g. multiple transaction sets per interchange),
    these will need independent counters instead of one shared value.

    After a successful file generation, the interchange number is
    incremented and persisted.
    """

    interchange: int = 1

    def __post_init__(self) -> None:
        if self.interchange < 1:
            raise ValueError(
                f"interchange must be a positive integer, got {self.interchange!r}"
            )

    # -------------------------------------------------------------------------
    # Formatted Values
    # -------------------------------------------------------------------------

    @property
    def isa13(self) -> str:
        """
        ISA13 - Interchange Control Number (fixed 9 digits).
        """
        if self.interchange > _ISA13_MAX:
            raise ValueError(
                f"interchange {self.interchange} exceeds the 9-digit ISA13 "
                f"limit ({_ISA13_MAX}) -- control number needs to be reset "
                f"or the field can no longer represent it"
            )

        return f"{self.interchange:0{_ISA13_WIDTH}d}"

    @property
    def gs06(self) -> str:
        """
        GS06 - Group Control Number. No documented minimum length.
        """
        return str(self.interchange)

    @property
    def st02(self) -> str:
        """
        ST02 - Transaction Set Control Number. Companion guide requires a
        minimum length of 4 characters, so this is zero-padded to at
        least 4 digits (matching SE02 must use this same padded value).
        """
        return f"{self.interchange:0{_ST02_MIN_WIDTH}d}"

    # -------------------------------------------------------------------------
    # Increment
    # -------------------------------------------------------------------------

    def increment(self) -> None:
        """
        Advances the control number for the next file. Only call this
        after the current file has been fully and successfully written --
        incrementing before that risks skipping or, worse, reusing a
        control number if a crash occurs between generation and save.
        """
        self.interchange += 1


# =============================================================================
# Persistence
# =============================================================================

def load_control_numbers(
    filename: str | Path = DEFAULT_FILENAME,
) -> ControlNumbers:
    """
    Loads the persisted control numbers.

    If the file does not exist, default values are returned. If the file
    exists but is unreadable or malformed (e.g. hand-edited incorrectly),
    raises a clear, actionable error rather than a raw JSON/type error.
    """

    path = Path(filename)

    if not path.exists():
        return ControlNumbers()

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} is not valid JSON ({exc}). If this file was edited "
            f"by hand, check for a missing comma, brace, or quote. If "
            f"you're not sure how to fix it, you can delete the file and "
            f"a fresh one starting at 1 will be created -- but note this "
            f"means your next control numbers may repeat ones already "
            f"sent to your trading partner."
        ) from exc

    try:
        return ControlNumbers(**data)

    except TypeError as exc:
        raise ValueError(
            f"{path} has an unexpected structure ({exc}). Expected a "
            f"single key: \"interchange\"."
        ) from exc


def save_control_numbers(
    control: ControlNumbers,
    filename: str | Path = DEFAULT_FILENAME,
) -> None:
    """
    Saves the current control numbers.

    Writes to a temporary file and renames it into place, so a crash or
    interruption mid-write can't leave control_numbers.json truncated or
    corrupted -- the rename only happens after the full write succeeds.
    """

    path = Path(filename)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as fp:
        json.dump(asdict(control), fp, indent=4)
        fp.flush()
        os.fsync(fp.fileno())

    tmp_path.replace(path)