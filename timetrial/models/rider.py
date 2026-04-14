"""Rider data model."""

from dataclasses import dataclass


@dataclass
class Rider:
    """A registered rider in the time trial."""

    bib_number: str
    last_name: str
    first_name: str
    category: str
    start_position: float  # Float minutes from race start (0.5 = 30s, 1.0 = 60s)

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def start_offset_ms(self) -> int:
        """Milliseconds from race start to this rider's start."""
        return int(self.start_position * 60 * 1000)

    @property
    def is_placeholder(self) -> bool:
        """True if this is an empty/deleted slot."""
        return self.bib_number == "----"
