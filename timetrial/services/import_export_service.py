"""CSV and HTML import/export — backwards-compatible with existing data files."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

from timetrial.models.rider import Rider
from timetrial.models.race import FinishRecord
from timetrial.models.result import RaceResult, NO_RESULT_SENTINEL
from timetrial.models.series import SeriesEntry
from timetrial.config.settings import AppConfig


# ---------------------------------------------------------------------------
# Data containers returned by import methods
# ---------------------------------------------------------------------------

class StartListData:
    """Parsed start list: riders plus any finish/result strings from the CSV."""

    __slots__ = ("riders", "finish_times", "results")

    def __init__(self) -> None:
        self.riders: list[Rider] = []
        # Keyed by bib — preserves finish_time / result strings from the CSV
        self.finish_times: dict[str, str] = {}
        self.results: dict[str, str] = {}


class FinishListData:
    """Parsed finish list rows."""

    __slots__ = ("rows",)

    def __init__(self) -> None:
        # Each row: (bib, last, first, category, finish_time_str, result_str)
        self.rows: list[tuple[str, str, str, str, str, str]] = []


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ImportExportService:
    """Read/write CSV and HTML files in formats compatible with the legacy app."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    # -----------------------------------------------------------------------
    # Start List  (7 columns)
    # -----------------------------------------------------------------------

    def import_start_list(self, path: Path) -> StartListData:
        """Parse a start-list CSV.

        Expected columns (header row skipped):
            BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT

        Returns a StartListData with riders and any stored finish/result strings.

        Raises ValueError on malformed rows.
        """
        data = StartListData()
        text = _read_text_flexible(path)

        for line_no, line in enumerate(text.splitlines(), start=1):
            # Skip header
            if line_no == 1:
                continue

            stripped = line.strip()
            if not stripped:
                continue

            fields = stripped.split(",")
            if len(fields) != 7:
                raise ValueError(
                    f"Start list line {line_no}: expected 7 fields, got {len(fields)}: {stripped!r}"
                )

            bib = fields[0].strip()
            last = fields[1].strip()
            first = fields[2].strip()
            category = fields[3].strip()
            position_str = fields[4].strip()
            finish = fields[5].strip()
            result = fields[6].strip()

            try:
                position = float(position_str)
            except ValueError:
                raise ValueError(
                    f"Start list line {line_no}: invalid start position {position_str!r}"
                )

            rider = Rider(
                bib_number=bib,
                last_name=last,
                first_name=first,
                category=category,
                start_position=position,
            )
            data.riders.append(rider)
            data.finish_times[bib] = finish
            data.results[bib] = result

        return data

    def export_start_list(
        self,
        path: Path,
        riders: list[Rider],
        finish_times: Optional[dict[str, str]] = None,
        results: Optional[dict[str, str]] = None,
    ) -> None:
        """Write a start-list CSV.

        Data rows use comma-only separation (no spaces) matching the legacy app's
        export format.  The header uses comma-space for readability.
        """
        finish_times = finish_times or {}
        results = results or {}

        lines: list[str] = []
        lines.append(
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT"
        )

        for rider in riders:
            finish = finish_times.get(rider.bib_number, NO_RESULT_SENTINEL)
            result = results.get(rider.bib_number, NO_RESULT_SENTINEL)
            # Format position: drop trailing .0 for whole numbers
            pos = _format_position(rider.start_position)
            lines.append(
                f"{rider.bib_number},{rider.last_name},{rider.first_name},"
                f"{rider.category},{pos},{finish},{result}"
            )

        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")

    # -----------------------------------------------------------------------
    # Finish List  (6 columns)
    # -----------------------------------------------------------------------

    def import_finish_list(self, path: Path) -> FinishListData:
        """Parse a finish-list CSV.

        Expected columns (header row skipped):
            BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, FINISH_TIME, RESULT

        Applies the legacy finish-time padding rule: if finish time < 12 chars,
        append '0'.
        """
        data = FinishListData()
        text = path.read_text(encoding="utf-8-sig")

        for line_no, line in enumerate(text.splitlines(), start=1):
            if line_no == 1:
                continue

            stripped = line.strip()
            if not stripped:
                continue

            fields = stripped.split(",")
            if len(fields) != 6:
                raise ValueError(
                    f"Finish list line {line_no}: expected 6 fields, got {len(fields)}: {stripped!r}"
                )

            bib = fields[0].strip()
            last = fields[1].strip()
            first = fields[2].strip()
            category = fields[3].strip()
            finish = fields[4].strip()
            result = fields[5].strip()

            # Legacy padding: ensure finish time has 3 decimal places
            if finish and finish != NO_RESULT_SENTINEL and len(finish) < 12:
                finish = finish + "0"

            data.rows.append((bib, last, first, category, finish, result))

        return data

    def export_finish_list(
        self,
        path: Path,
        rows: list[tuple[str, str, str, str, str, str]],
    ) -> None:
        """Write a finish-list CSV.

        Each row is (bib, last, first, category, finish_time, result).
        """
        lines: list[str] = []
        lines.append("BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, FINISH_TIME, RESULT")

        for bib, last, first, category, finish, result in rows:
            lines.append(f"{bib},{last},{first},{category},{finish},{result}")

        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")

    # -----------------------------------------------------------------------
    # Series  (4-column CSV that the app produces / consumes)
    # -----------------------------------------------------------------------

    def import_series(self, path: Path) -> list[SeriesEntry]:
        """Parse a series-points CSV.

        The legacy app's own format is 4 columns:
            FIRST_NAME, LAST_NAME, CATEGORY, POINTS

        We also support the 3-column hand-edited format:
            CATEGORY, NAME, POINTS
        where NAME is "First Last".

        Blank/separator rows (e.g. ",,") are skipped.
        """
        entries: list[SeriesEntry] = []
        text = path.read_text(encoding="utf-8-sig")

        for line_no, line in enumerate(text.splitlines(), start=1):
            if line_no == 1:
                continue  # skip header

            stripped = line.strip()
            if not stripped:
                continue

            fields = stripped.split(",")

            # Skip separator rows like ",,"
            non_empty = [f.strip() for f in fields if f.strip()]
            if not non_empty:
                continue

            if len(fields) == 4:
                # App's own format: first, last, category, points
                first = fields[0].strip()
                last = fields[1].strip()
                category = fields[2].strip()
                points = int(fields[3].strip())
            elif len(fields) == 3:
                # Hand-edited format: category, name, points
                category = fields[0].strip()
                name = fields[1].strip()
                points = int(fields[2].strip())
                parts = name.split(None, 1)
                first = parts[0] if parts else ""
                last = parts[1] if len(parts) > 1 else ""
            else:
                continue  # skip malformed rows

            if not category:
                continue  # skip rows with blank category

            entries.append(SeriesEntry(
                first_name=first,
                last_name=last,
                category=category,
                total_points=points,
            ))

        return entries

    def export_series(self, path: Path, entries: list[SeriesEntry]) -> None:
        """Write a series-points CSV in the app's 4-column format."""
        lines: list[str] = []
        lines.append("FIRST_NAME,LAST_NAME,CATEGORY,POINTS")

        for entry in entries:
            lines.append(
                f"{entry.first_name},{entry.last_name},{entry.category},{entry.total_points}"
            )

        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")

    # -----------------------------------------------------------------------
    # HTML export
    # -----------------------------------------------------------------------

    def export_html(self, path: Path, html: str) -> None:
        """Write an HTML string to a file."""
        path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_text_flexible(path: Path) -> str:
    """Read a text file, trying UTF-8 first then falling back to Windows-1252."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def _format_position(position: float) -> str:
    """Format a start position: '1' for whole numbers, '0.5' / '1.5' for halves."""
    if position == int(position):
        return str(int(position))
    return str(position)
