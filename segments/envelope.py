from __future__ import annotations

from config import Config
from control_numbers import ControlNumbers
from edi_writer import X12Writer

from utils import gs_date, gs_time, isa_date, isa_time

from x12_constants import (
    ACKNOWLEDGEMENT_REQUESTED,
    COMPONENT_ELEMENT_SEPARATOR,
    FUNCTIONAL_IDENTIFIER,
    IMPLEMENTATION_VERSION,
    ISA_AUTHORIZATION_INFORMATION,
    ISA_AUTHORIZATION_QUALIFIER,
    ISA_RECEIVER_QUALIFIER,
    ISA_REPETITION_SEPARATOR,
    ISA_SECURITY_INFORMATION,
    ISA_SECURITY_QUALIFIER,
    ISA_SENDER_QUALIFIER,
    TRANSACTION_SET_IDENTIFIER,
    X12_VERSION,
)


def pad(value: str, length: int) -> str:
    return (value or "")[:length].ljust(length)


class X12EnvelopeManager:
    """
    Handles ISA/GS/ST on open() and SE/GE/IEA on close() for a single
    834 transaction set.
    """

    def __init__(self, config: Config, control: ControlNumbers, writer: X12Writer):
        self.config = config
        self.control = control
        self.writer = writer

    def open(self) -> None:
        self._write_isa()
        self._write_gs()
        self._write_st()

    def close(self) -> None:
        self._write_se()
        self._write_ge()
        self._write_iea()

    # -------------------------------------------------------------------
    # OPEN
    # -------------------------------------------------------------------

    def _write_isa(self) -> None:
        self.writer.segment(
            "ISA",
            ISA_AUTHORIZATION_QUALIFIER,
            pad(ISA_AUTHORIZATION_INFORMATION, 10),
            ISA_SECURITY_QUALIFIER,
            pad(ISA_SECURITY_INFORMATION, 10),
            ISA_SENDER_QUALIFIER,
            pad(self.config.sender_id, 15),
            ISA_RECEIVER_QUALIFIER,
            pad(self.config.receiver_id, 15),
            isa_date(),
            isa_time(),
            ISA_REPETITION_SEPARATOR,
            X12_VERSION,
            self.control.isa13,
            ACKNOWLEDGEMENT_REQUESTED,
            self.config.usage_indicator,
            COMPONENT_ELEMENT_SEPARATOR,
        )

    def _write_gs(self) -> None:
        self.writer.segment(
            "GS",
            FUNCTIONAL_IDENTIFIER,
            self.config.sender_id,
            self.config.receiver_id,
            gs_date(),
            gs_time(),
            self.control.gs06,
            "X",
            IMPLEMENTATION_VERSION,
        )

    def _write_st(self) -> None:
        self.writer.begin_transaction()
        self.writer.segment(
            "ST",
            TRANSACTION_SET_IDENTIFIER,
            self.control.st02,
            IMPLEMENTATION_VERSION,
        )

    # -------------------------------------------------------------------
    # CLOSE
    # -------------------------------------------------------------------

    def _write_se(self) -> None:
        self.writer.segment(
            "SE",
            self.writer.transaction_segment_count(),
            self.control.st02,
        )

    def _write_ge(self) -> None:
        self.writer.segment(
            "GE",
            "1",
            self.control.gs06,
        )

    def _write_iea(self) -> None:
        self.writer.segment(
            "IEA",
            "1",
            self.control.isa13,
        )