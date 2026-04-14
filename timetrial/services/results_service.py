"""Result calculation, sorting, and HTML generation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from timetrial.config.settings import AppConfig
from timetrial.models.rider import Rider
from timetrial.models.race import Race, FinishRecord
from timetrial.models.result import RaceResult, NO_RESULT_SENTINEL


class ResultsService:
    """Pure computation — no timer, no UI."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Single result calculation
    # ------------------------------------------------------------------

    def calculate_result(
        self,
        rider: Rider,
        finish_time_str: str,
        race_start: datetime,
    ) -> RaceResult:
        """Calculate elapsed time for one rider.

        Args:
            rider: The rider (provides start_position for offset).
            finish_time_str: Wall-clock finish time as "hh:mm:ss.zzz".
            race_start: The absolute datetime when the race clock started.

        Returns:
            A RaceResult with computed elapsed time.
        """
        # Build the rider's absolute start time
        start_dt = race_start + timedelta(milliseconds=rider.start_offset_ms)

        # Parse finish time: take the date from race_start, replace time component
        finish_time = _parse_time_str(finish_time_str)
        finish_dt = race_start.replace(
            hour=finish_time.hour,
            minute=finish_time.minute,
            second=finish_time.second,
            microsecond=finish_time.microsecond,
        )

        # Elapsed milliseconds
        elapsed_ms = int((finish_dt - start_dt).total_seconds() * 1000)

        # Format elapsed as hh:mm:ss.zzz
        result_time_str = _format_elapsed_ms(elapsed_ms)

        return RaceResult(
            bib_number=rider.bib_number,
            first_name=rider.first_name,
            last_name=rider.last_name,
            category=rider.category,
            finish_time_str=finish_time_str,
            result_time_str=result_time_str,
            result_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Batch computation from race state
    # ------------------------------------------------------------------

    def compute_all_results(
        self,
        race: Race,
        finish_times: dict[str, str],
        result_strings: dict[str, str],
    ) -> list[RaceResult]:
        """Build RaceResult list from riders and their finish data.

        This works with the finish_times/results dicts that the start list
        tracks (keyed by bib).  If race.start_time is set and a finish_time
        is present, the elapsed time is (re-)calculated.  If only a
        pre-computed result string is available, it's used as-is.

        Args:
            race: The race (provides riders and start_time).
            finish_times: bib → wall-clock finish time string.
            result_strings: bib → pre-computed result string (from CSV import).

        Returns:
            List of RaceResult for every rider that has a valid result.
        """
        results: list[RaceResult] = []

        for rider in race.riders:
            if rider.is_placeholder or rider.category == "----":
                continue

            finish_str = finish_times.get(rider.bib_number, NO_RESULT_SENTINEL)
            result_str = result_strings.get(rider.bib_number, NO_RESULT_SENTINEL)

            if finish_str == NO_RESULT_SENTINEL and result_str == NO_RESULT_SENTINEL:
                continue

            # If we have a race start time and a finish time, compute fresh
            if race.start_time and finish_str != NO_RESULT_SENTINEL:
                try:
                    result = self.calculate_result(rider, finish_str, race.start_time)
                    results.append(result)
                    continue
                except (ValueError, OverflowError):
                    pass  # fall through to use pre-computed string

            # Otherwise use the stored result string
            if result_str != NO_RESULT_SENTINEL:
                elapsed_ms = _parse_result_to_ms(result_str)
                results.append(RaceResult(
                    bib_number=rider.bib_number,
                    first_name=rider.first_name,
                    last_name=rider.last_name,
                    category=rider.category,
                    finish_time_str=finish_str,
                    result_time_str=result_str,
                    result_ms=elapsed_ms,
                ))

        return results

    # ------------------------------------------------------------------
    # Grouping and filtering
    # ------------------------------------------------------------------

    def category_results(self, results: list[RaceResult]) -> dict[str, list[RaceResult]]:
        """Group results by category, each group sorted by elapsed time."""
        groups: dict[str, list[RaceResult]] = {}
        for r in results:
            if not r.has_result:
                continue
            groups.setdefault(r.category, []).append(r)

        for group in groups.values():
            group.sort(key=lambda r: r.result_ms)

        return groups

    def overall_results(self, results: list[RaceResult]) -> list[RaceResult]:
        """All results excluding junior categories, sorted fastest to slowest."""
        junior = set(self._config.junior_categories)
        filtered = [
            r for r in results
            if r.has_result and r.category not in junior
        ]
        filtered.sort(key=lambda r: r.result_ms)
        return filtered

    # ------------------------------------------------------------------
    # HTML generation — matches legacy format
    # ------------------------------------------------------------------

    def generate_results_html(self, results: list[RaceResult]) -> str:
        """Produce the combined Category + Overall HTML report.

        Replicates the legacy app's <pre>-based formatting so existing
        workflows (printing, copy-paste) are unaffected.
        """
        cat_results = self.category_results(results)
        ovr_results = self.overall_results(results)

        # --- Category Results ---
        # Build sorted lines in the legacy format:
        #   "Category            Result      Name"
        # Sorted alphabetically (which groups categories together).
        cat_lines: list[str] = []
        for r in results:
            if not r.has_result:
                continue
            # Legacy format: "%-18s  %s  %-24s"
            # result truncated to first 10 chars (drops the last ms digit for display)
            line = f"{r.category:<18s}  {r.result_time_str[:10]}  {r.display_name}"
            cat_lines.append(line)
        cat_lines.sort()

        # --- Build HTML ---
        html_parts: list[str] = []
        html_parts.append("<html><body>")
        html_parts.append("<h2>Category Results</h2>")
        html_parts.append("<pre>")

        # Insert blank line between different categories
        prev_prefix = ""
        for line in cat_lines:
            current_prefix = line[:15]
            if prev_prefix and current_prefix != prev_prefix:
                html_parts.append("")
            html_parts.append(line)
            prev_prefix = current_prefix

        html_parts.append("</pre>")
        html_parts.append("<p>")
        html_parts.append("<h2>Overall Results</h2>")
        html_parts.append("<pre>")

        for i, r in enumerate(ovr_results, start=1):
            line = f"{i:3d})  {r.result_time_str[:10]}  {r.display_name:<24s}  {r.category}"
            html_parts.append(line)

        html_parts.append("</pre>")
        html_parts.append("</body></html>")

        return "\n".join(html_parts) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_time_str(time_str: str) -> datetime:
    """Parse 'hh:mm:ss.zzz' into a datetime (date part is 1900-01-01)."""
    # Handle both 3-digit ms (.zzz) and 2-digit (.zz)
    parts = time_str.split(".")
    base = parts[0]
    ms_str = parts[1] if len(parts) > 1 else "000"
    # Pad to 3 digits
    ms_str = ms_str.ljust(3, "0")[:3]
    return datetime.strptime(f"{base}.{ms_str}", "%H:%M:%S.%f")


def _format_elapsed_ms(elapsed_ms: int) -> str:
    """Format milliseconds as 'hh:mm:ss.zzz'."""
    if elapsed_ms < 0:
        elapsed_ms = 0

    total_seconds = elapsed_ms // 1000
    ms = elapsed_ms % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"


def _parse_result_to_ms(result_str: str) -> int:
    """Parse 'hh:mm:ss.zzz' elapsed time string to milliseconds."""
    if result_str == NO_RESULT_SENTINEL:
        return 0

    try:
        parts = result_str.split(".")
        base = parts[0]
        ms_str = parts[1] if len(parts) > 1 else "000"
        ms_str = ms_str.ljust(3, "0")[:3]

        time_parts = base.split(":")
        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        seconds = int(time_parts[2])

        return ((hours * 3600 + minutes * 60 + seconds) * 1000) + int(ms_str)
    except (ValueError, IndexError):
        return 0
