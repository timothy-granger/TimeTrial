"""Series standings model."""

from dataclasses import dataclass


@dataclass
class SeriesEntry:
    """Cumulative series standing for one rider."""

    first_name: str
    last_name: str
    category: str
    total_points: int

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
