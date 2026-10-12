from pathlib import Path

from config import Config
from control_numbers import ControlNumbers, save_control_numbers
from edi_writer import X12Writer
from models import Subscriber

# TODO: verify this import once segments/envelope.py is reviewed --
# there's no top-level x12_envelope.py in the project layout, only
# segments/envelope.py. Update once the actual class name is confirmed.
from segments.envelope import X12EnvelopeManager
from segments.sponsor import write_sponsor_information
from segments.header import write_transaction_header
from edi_renderer import render_members
from edi_834_validator import validate_834


class EDI834Generator:
    """
    High-level orchestration only.
    No X12 logic here anymore.
    """

    def __init__(self, config: Config, control_numbers: ControlNumbers):
        self.config = config
        self.control = control_numbers

    def generate(self, subscribers: list[Subscriber], output_file: str | Path) -> None:

        writer = X12Writer()

        envelope = X12EnvelopeManager(self.config, self.control, writer)

        # -------------------------
        # VALIDATE
        # -------------------------
        validate_834(subscribers)

        # -------------------------
        # OPEN
        # -------------------------
        envelope.open()

        write_transaction_header(writer, self.config)      # BGN + REF*38*
        write_sponsor_information(writer, self.config)     # N1 1000A + 1000B

        # -------------------------
        # BODY
        # -------------------------
        render_members(
            writer,
            subscribers,
            tier_structure=self.config.tier_structure,
            group_number=self.config.group_number,
        )

        # -------------------------
        # CLOSE
        # -------------------------
        envelope.close()

        # -------------------------
        # WRITE FILE
        # -------------------------
        writer.write(output_file)

        # -------------------------
        # COMMIT CONTROL NUMBERS
        #
        # FIX: was calling self.control.bump_all(), which doesn't exist
        # on ControlNumbers -- this crashed after the file was already
        # written, leaving an unaccounted-for file on disk with control
        # numbers never incremented/saved.
        # -------------------------
        self.control.increment()
        save_control_numbers(self.control)