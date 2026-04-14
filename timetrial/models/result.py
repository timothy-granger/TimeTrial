"""Race result model."""

from dataclasses import dataclass

NO_RESULT_SENTINEL = "--:--:--.---"


@dataclass
class RaceResult:
    """A calculated race result for one rider."""

    bib_number: str
    first_name: str
    last_name: str
    category: str
    finish_time_str: str   # Wall-clock finish time "hh:mm:ss.zzz"
    result_time_str: str   # Elapsed riding time "hh:mm:ss.zzz"
    result_ms: int         # Elapsed milliseconds (for sorting)

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def has_result(self) -> bool:
        return self.result_time_str != NO_RESULT_SENTINEL
