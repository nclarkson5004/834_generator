from __future__ import annotations

from pathlib import Path

from x12_constants import (
    ELEMENT_SEPARATOR,
    SEGMENT_TERMINATOR,
)


class X12Writer:
    """
    Writes an X12 EDI document.

    Responsibilities:
        - Format segments
        - Count segments
        - Track ST/SE transaction boundaries
        - Write completed document to disk

    This class intentionally knows nothing about the 834 format.
    """

    def __init__(self) -> None:
        self._segments: list[str] = []
        self._segment_count = 0
        self._transaction_start: int | None = None

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def segment_count(self) -> int:
        return self._segment_count

    @property
    def transaction_started(self) -> bool:
        return self._transaction_start is not None

    @property
    def segments(self) -> tuple[str, ...]:
        """
        Read-only access to generated segments.
        """
        return tuple(self._segments)

    # -------------------------------------------------------------------------
    # Transaction Control
    # -------------------------------------------------------------------------

    def begin_transaction(self) -> None:
        """
        Marks the position of the ST segment.
        """
        self._transaction_start = self._segment_count

    def clear(self) -> None:
        """
        Clears all generated output.
        """
        self._segments.clear()
        self._segment_count = 0
        self._transaction_start = None

    # -------------------------------------------------------------------------
    # Segment Writing
    # -------------------------------------------------------------------------

    def segment(self, *elements: object) -> int:
        """
        Writes a single X12 segment.

        None values become empty elements.
        """

        if not elements:
            raise ValueError("Cannot write an empty segment.")

        values = [
            "" if value is None else str(value)
            for value in elements
        ]

        self._segments.append(
            ELEMENT_SEPARATOR.join(values)
            + SEGMENT_TERMINATOR
        )

        self._segment_count += 1

        return self._segment_count

    def extend(
        self,
        segments: list[list[object]],
    ) -> None:
        """
        Writes multiple segments.
        """

        for segment in segments:
            self.segment(*segment)

    # -------------------------------------------------------------------------
    # Transaction Counts
    # -------------------------------------------------------------------------

    def segments_since_transaction_start(self) -> int:
        """
        Number of segments written since ST.
        """

        if self._transaction_start is None:
            raise RuntimeError(
                "Transaction has not been started."
            )

        return self._segment_count - self._transaction_start

    def transaction_segment_count(self) -> int:
        """
        Returns the value for SE01.

        Includes:

            ST
            ...
            SE
        """

        return self.segments_since_transaction_start() + 1

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def render(self) -> str:
        """
        Returns the completed EDI document.
        """

        return "".join(self._segments)

    #
    # Backwards compatibility.
    #

    def text(self) -> str:
        return self.render()

    def write(
        self,
        filename: str | Path,
    ) -> None:

        path = Path(filename)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as fp:

            fp.write(self.render())