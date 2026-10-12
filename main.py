import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from config import load_config
from control_numbers import load_control_numbers
from generator import EDI834Generator
from parser import read_census
from x12_constants import LOGGER_NAME


# =============================================================================
# LOGGING
# =============================================================================

def configure_logging(log_file: Path) -> None:
    """
    Logs warnings/errors to both the console and a persistent log file
    next to the output, so issues (bad dates, unrecognized values, etc.)
    are visible after the fact -- not just scrolled past in a console
    window that gets closed.
    """

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


logger = logging.getLogger(LOGGER_NAME)


# =============================================================================
# ARG PARSING
# =============================================================================

def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Generate an ANSI X12 834 Enrollment File."
    )

    parser.add_argument(
        "csv_file",
        help="Enrollment census CSV file.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output 834 filename. Defaults to a dated filename inside "
            "the output_directory configured in settings.json."
        ),
    )

    return parser.parse_args()


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    args = parse_arguments()

    csv_file = Path(args.csv_file)

    if not csv_file.exists():
        print(f"ERROR: File does not exist:\n{csv_file}")
        return 1

    # -------------------------------------------------------------
    # CONFIG (loaded before logging is configured, so we know
    # output_directory before deciding where the log file goes)
    # -------------------------------------------------------------

    config = load_config()

    output_dir = Path(config.output_directory)

    if args.output:
        output_file = Path(args.output)
    else:
        output_file = output_dir / f"enrollment_{date.today():%Y%m%d}.834"

    configure_logging(output_dir / "generation.log")

    print("----------------------------------------")
    print("834 Enrollment File Generator")
    print("----------------------------------------\n")

    logger.info("Loading control numbers...")

    # NOTE: control_numbers.json path defaults relative to CWD, same
    # risk flagged for settings.json previously -- consider resolving
    # it relative to a fixed project location rather than the process's
    # working directory if this is ever run via double-click / a
    # scheduled task.
    control_numbers = load_control_numbers()

    # -------------------------------------------------------------
    # CSV PARSE
    # -------------------------------------------------------------

    logger.info("Reading census: %s", csv_file)

    try:
        subscribers = read_census(csv_file)
    except Exception as exc:
        logger.exception("Failed to parse census CSV")
        print(f"\nERROR parsing CSV:\n{exc}")
        return 1

    logger.info("Loaded %d subscriber(s).", len(subscribers))

    # -------------------------------------------------------------
    # GENERATION (includes validation -- see generator.py)
    # -------------------------------------------------------------

    generator = EDI834Generator(
        config,
        control_numbers,
    )

    logger.info("Generating: %s", output_file)

    try:
        generator.generate(subscribers, output_file)

    except Exception as exc:
        logger.exception("Generation failed")
        print("\n----------------------------------------")
        print("GENERATION FAILED")
        print("----------------------------------------")
        print(f"{exc}")
        print(
            f"\nCheck the log for details: {output_dir / 'generation.log'}"
        )
        return 1

    print("\n----------------------------------------")
    print("SUCCESS")
    print("----------------------------------------")
    print(f"834 written to:\n{output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())