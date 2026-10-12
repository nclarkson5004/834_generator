from config import Config
from edi_writer import X12Writer
from utils import sanitize_edi


# =============================================================================
# 1000A - SPONSOR
# =============================================================================

def write_sponsor(
    writer: X12Writer,
    config: Config,
) -> None:

    if not config.sponsor_name:
        raise ValueError("Missing sponsor_name in config")

    writer.segment(
        "N1",
        "P5",
        sanitize_edi(config.sponsor_name),
        "FI",
        config.sponsor_tax_id,   # FIX: consistent sponsor identity
    )


# =============================================================================
# 1000B - PAYER
# =============================================================================

def write_payer(
    writer: X12Writer,
    config: Config,
) -> None:

    if not config.payer_name or not config.payer_identifier:
        raise ValueError("Missing payer configuration (name or identifier)")

    writer.segment(
        "N1",
        "IN",
        sanitize_edi(config.payer_name),
        "FI",
        config.payer_identifier,
    )


# =============================================================================
# ORCHESTRATION
# =============================================================================

def write_sponsor_information(
    writer: X12Writer,
    config: Config,
) -> None:

    write_sponsor(writer, config)
    write_payer(writer, config)