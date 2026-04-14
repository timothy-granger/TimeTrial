"""Race state and finish record models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class RaceState(Enum):
    NOT_STARTED = auto()
    RUNNING = auto()
    STOPPED = auto()


@dataclass
class FinishRecord:
    """A raw finish capture: timestamp first, bib associated later."""

    finish_timestamp: datetime
    bib_number: Optional[str] = None

    @property
    def is_identified(self) -> bool:
        return self.bib_number is not None and self.bib_number.strip() != ""


@dataclass
class Race:
    """Top-level race state container."""

    start_time: Optional[datetime] = None
    state: RaceState = field(default=RaceState.NOT_STARTED)
    riders: list = field(default_factory=list)          # list[Rider], sorted by start_position
    finish_records: list = field(default_factory=list)   # list[FinishRecord], in capture order
    current_rider_index: int = 0                         # Index into riders for starter sequencing

    def rider_by_bib(self, bib: str) -> Optional["Rider"]:
        """Look up a rider by bib number. Returns None if not found."""
        for rider in self.riders:
            if rider.bib_number == bib:
                return rider
        return None

    def next_start_position(self, interval: float = 0.5) -> float:
        """Find the first available start position (in minutes).

        Searches from `interval` upward in `interval` increments,
        returning the first position not already assigned.
        """
        taken = {r.start_position for r in self.riders if not r.is_placeholder}
        pos = interval
        while pos in taken:
            pos += interval
        return pos

    def insert_rider_sorted(self, rider: "Rider") -> int:
        """Insert a rider maintaining sort order by start_position.

        Returns the index where the rider was inserted.
        """
        from timetrial.models.rider import Rider  # noqa: F811 — avoid circular at module level

        idx = 0
        for idx, existing in enumerate(self.riders):
            if rider.start_position < existing.start_position:
                self.riders.insert(idx, rider)
                return idx
        else:
            self.riders.append(rider)
            return len(self.riders) - 1

    def is_bib_taken(self, bib: str, exclude_bib: Optional[str] = None) -> bool:
        """Check if a bib number is already in use."""
        for rider in self.riders:
            if rider.bib_number == bib and rider.bib_number != exclude_bib:
                return True
        return False

    def is_position_taken(self, position: float, exclude_bib: Optional[str] = None) -> bool:
        """Check if a start position is already in use."""
        for rider in self.riders:
            if rider.start_position == position:
                if exclude_bib is None or rider.bib_number != exclude_bib:
                    return True
        return False
