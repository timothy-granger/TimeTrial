"""Convert Google Forms registration CSV into a TimeTrial start list.

Google Forms exports a CSV with columns:
    Timestamp, Last Name, First Name, Category, Preferred Start Window

This tool reads that CSV, groups riders by preferred window then category,
assigns bib numbers and 30-second start positions, and writes the standard
7-column start list CSV the app expects.

Usage:
    python -m timetrial.tools.registration_import <input_csv> [output_csv]

    input_csv   Path to the Google Forms CSV export
    output_csv  Path for generated start list (default: tt-start-list.csv
                in the same directory as the input)

Options:
    --bib-start N       First bib number to assign (default: 1)
    --bib-end N         Last bib number available (default: 100)
    --interval M        Start interval in minutes (default: 0.5 = 30 sec)
    --start-offset M    First rider's start position in minutes (default: 0.5)
    --dry-run           Print the start list to stdout without writing a file
    --publish           Publish start list to GitHub Pages (tt-live-results)
    --race-name TEXT    Race name for published start list
    --event-info TEXT   Event info line (e.g. date)
    --race-time HH:MM  Race start time for display (default: 18:00)
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from timetrial.models.rider import Rider
from timetrial.models.result import NO_RESULT_SENTINEL


# ---------------------------------------------------------------------------
# Categories for 2026 club events (ordered by desired start sequence)
# ---------------------------------------------------------------------------

CLUB_CATEGORIES = [
    "Men (P/1/2/3)",
    "Men (4/5/U)",
    "Women (P/1/2/3)",
    "Women (4/U)",
    "Masters 50+ - Men",
    "Masters 50+ - Women",
    "Masters 60+ - Men",
    "Masters 60+ - Women",
    "Masters 70+ - Men",
    "Masters 70+ - Women",
    "Merckx - Men",
    "Merckx - Women",
    "Juniors (M)",
    "Juniors (F)",
    "Hand Cycle (M)",
]

# Preferred start windows — display label → sort order
WINDOW_ORDER = {
    "Early (6:00 - 6:15)": 0,
    "Middle (6:16 - 6:30)": 1,
    "Late (6:31 - 6:45)": 2,
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class Registration:
    """One registration row from the Google Forms CSV."""

    __slots__ = ("last_name", "first_name", "category", "window")

    def __init__(self, last: str, first: str, category: str, window: str) -> None:
        self.last_name = last.strip()
        self.first_name = first.strip()
        self.category = category.strip()
        self.window = window.strip()

    def __repr__(self) -> str:
        return (
            f"Registration({self.first_name} {self.last_name}, "
            f"{self.category}, {self.window})"
        )


def parse_registrations(path: Path) -> list[Registration]:
    """Read a Google Forms CSV export and return Registration objects.

    Expected columns (by header name, order-independent):
        Timestamp          (ignored)
        Last Name
        First Name
        Category
        Preferred Start Window

    Raises ValueError on missing columns or empty required fields.
    """
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())

    # Normalize header names for flexible matching
    if reader.fieldnames is None:
        raise ValueError(f"Empty CSV file: {path}")

    field_map = {f.strip().lower(): f for f in reader.fieldnames}
    required = {
        "last name": "Last Name",
        "first name": "First Name",
        "category": "Category",
        "preferred start window": "Preferred Start Window",
    }

    # Resolve actual column names from the header
    resolved: dict[str, str] = {}
    for key, display in required.items():
        actual = field_map.get(key)
        if actual is None:
            raise ValueError(
                f"Missing required column '{display}' in {path}. "
                f"Found columns: {list(reader.fieldnames)}"
            )
        resolved[key] = actual

    registrations: list[Registration] = []
    for row_num, row in enumerate(reader, start=2):
        last = row[resolved["last name"]].strip()
        first = row[resolved["first name"]].strip()
        category = row[resolved["category"]].strip()
        window = row[resolved["preferred start window"]].strip()

        if not last or not first:
            print(f"  Warning: row {row_num} missing name, skipping: {row}")
            continue

        if not category:
            print(f"  Warning: row {row_num} missing category for {first} {last}, skipping")
            continue

        # Validate category
        if category not in CLUB_CATEGORIES:
            print(
                f"  Warning: row {row_num} unknown category '{category}' "
                f"for {first} {last} — including anyway"
            )

        # Validate window (accept unknown windows, sort them last)
        if window not in WINDOW_ORDER:
            print(
                f"  Warning: row {row_num} unknown window '{window}' "
                f"for {first} {last} — placing at end"
            )

        registrations.append(Registration(last, first, category, window))

    return registrations


# ---------------------------------------------------------------------------
# Start list generation
# ---------------------------------------------------------------------------

def _sort_key(reg: Registration) -> tuple[int, int, str, str]:
    """Sort registrations by window preference, then category order, then name."""
    window_rank = WINDOW_ORDER.get(reg.window, 999)
    cat_rank = (
        CLUB_CATEGORIES.index(reg.category)
        if reg.category in CLUB_CATEGORIES
        else 999
    )
    return (window_rank, cat_rank, reg.last_name.lower(), reg.first_name.lower())


def build_start_list(
    registrations: list[Registration],
    bib_start: int = 1,
    bib_end: int = 100,
    interval: float = 0.5,
    start_offset: float = 0.5,
) -> list[Rider]:
    """Convert registrations into a sorted list of Riders with assigned bibs.

    Riders are sorted by preferred window, then by category order, then by
    last name.  Bib numbers are assigned sequentially from bib_start.

    Returns a list of Rider objects ready for CSV export.
    """
    sorted_regs = sorted(registrations, key=_sort_key)

    available_bibs = bib_end - bib_start + 1
    if len(sorted_regs) > available_bibs:
        print(
            f"  Warning: {len(sorted_regs)} registrations but only "
            f"{available_bibs} bibs available ({bib_start}-{bib_end}). "
            f"Extra riders will get bibs beyond {bib_end}."
        )

    riders: list[Rider] = []
    for i, reg in enumerate(sorted_regs):
        bib = str(bib_start + i)
        position = start_offset + (i * interval)
        rider = Rider(
            bib_number=bib,
            last_name=reg.last_name,
            first_name=reg.first_name,
            category=reg.category,
            start_position=position,
        )
        riders.append(rider)

    return riders


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def _format_position(position: float) -> str:
    """Format start position: '1' for whole, '0.5' for half."""
    if position == int(position):
        return str(int(position))
    return str(position)


def write_start_list(path: Path, riders: list[Rider]) -> None:
    """Write the standard 7-column start list CSV."""
    lines: list[str] = []
    lines.append(
        "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT"
    )

    for rider in riders:
        pos = _format_position(rider.start_position)
        lines.append(
            f"{rider.bib_number},{rider.last_name},{rider.first_name},"
            f"{rider.category},{pos},{NO_RESULT_SENTINEL},{NO_RESULT_SENTINEL}"
        )

    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")


def print_start_list(riders: list[Rider]) -> None:
    """Print a formatted preview of the start list."""
    print(f"\n{'Bib':>4}  {'Last Name':<20} {'First Name':<15} {'Category':<25} {'Pos':>5}")
    print("-" * 75)
    prev_window_idx = -1
    for i, r in enumerate(riders):
        # Insert a blank line between time windows for readability
        minutes = r.start_position * 0.5  # rough minute estimate
        window_idx = 0 if i < 30 else (1 if i < 60 else 2)
        if window_idx != prev_window_idx and prev_window_idx >= 0:
            print()
        prev_window_idx = window_idx

        pos = _format_position(r.start_position)
        print(f"{r.bib_number:>4}  {r.last_name:<20} {r.first_name:<15} {r.category:<25} {pos:>5}")


def print_summary(riders: list[Rider]) -> None:
    """Print category and window distribution summary."""
    from collections import Counter

    cat_counts: Counter[str] = Counter()
    for r in riders:
        cat_counts[r.category] += 1

    print(f"\n{'Category':<30} {'Count':>5}")
    print("-" * 37)
    for cat in CLUB_CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count > 0:
            print(f"{cat:<30} {count:>5}")
    # Any unknown categories
    for cat, count in sorted(cat_counts.items()):
        if cat not in CLUB_CATEGORIES:
            print(f"{cat:<30} {count:>5}  (unknown)")

    total_minutes = (len(riders) - 1) * 0.5 if riders else 0
    print(f"\nTotal riders: {len(riders)}")
    print(f"Race duration: {total_minutes:.1f} minutes ({len(riders)} starts at 30-sec intervals)")
    last_pos = _format_position(riders[-1].start_position) if riders else "0"
    print(f"Last start position: {last_pos}")


# ---------------------------------------------------------------------------
# Publish start list to GitHub Pages
# ---------------------------------------------------------------------------

DEFAULT_REPO_PATH = Path("D:/tt-live-results")


def _format_start_time(position: float, race_time: str = "18:00") -> str:
    """Convert a start position (minutes) to a wall-clock time string.

    E.g. position=0.5 with race_time="18:00" → "6:00:30 PM"
    """
    parts = race_time.split(":")
    base_hour = int(parts[0])
    base_min = int(parts[1]) if len(parts) > 1 else 0

    total_seconds = int(position * 60)
    extra_minutes, seconds = divmod(total_seconds, 60)
    minute = base_min + extra_minutes
    hour = base_hour + minute // 60
    minute = minute % 60

    # 12-hour format
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12

    if seconds:
        return f"{display_hour}:{minute:02d}:{seconds:02d} {period}"
    return f"{display_hour}:{minute:02d} {period}"


def publish_start_list(
    riders: list[Rider],
    race_name: str = "Greenville Spinners Time Trial",
    event_info: str = "",
    race_time: str = "18:00",
    repo_path: Path = DEFAULT_REPO_PATH,
) -> None:
    """Write startlist.json to the GitHub Pages repo and push."""
    if not repo_path.exists():
        print(f"Error: repo not found at {repo_path}")
        sys.exit(1)

    data = {
        "race_name": race_name,
        "event_info": event_info,
        "updated_at": datetime.now().isoformat(),
        "start_list": [
            {
                "bib": r.bib_number,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "category": r.category,
                "start_time": _format_start_time(r.start_position, race_time),
                "start_position": r.start_position,
            }
            for r in riders
        ],
    }

    json_path = repo_path / "startlist.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                return result.stdout
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    print(f"Publishing start list ({len(riders)} riders) to GitHub Pages...")
    git("add", "startlist.json")
    git("commit", "-m", f"Publish start list: {len(riders)} riders")
    git("push")
    print(f"Start list published to GitHub Pages")
    print(f"Riders can view at: https://timothy-granger.github.io/tt-live-results/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert Google Forms registration CSV to TimeTrial start list"
    )
    parser.add_argument("input_csv", help="Path to Google Forms CSV export")
    parser.add_argument("output_csv", nargs="?", help="Output start list path (default: same dir)")
    parser.add_argument("--bib-start", type=int, default=1, help="First bib number (default: 1)")
    parser.add_argument("--bib-end", type=int, default=100, help="Last bib available (default: 100)")
    parser.add_argument("--interval", type=float, default=0.5, help="Start interval in minutes (default: 0.5)")
    parser.add_argument("--start-offset", type=float, default=0.5, help="First rider position (default: 0.5)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write file")
    parser.add_argument("--publish", action="store_true", help="Publish start list to GitHub Pages")
    parser.add_argument("--race-name", default="Greenville Spinners Time Trial", help="Race name for web display")
    parser.add_argument("--event-info", default="", help="Event info (e.g. date)")
    parser.add_argument("--race-time", default="18:00", help="Race start time HH:MM (default: 18:00)")

    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    # Parse registrations
    print(f"Reading registrations from: {input_path}")
    registrations = parse_registrations(input_path)
    print(f"Found {len(registrations)} valid registrations")

    if not registrations:
        print("No registrations to process.")
        sys.exit(0)

    # Build start list
    riders = build_start_list(
        registrations,
        bib_start=args.bib_start,
        bib_end=args.bib_end,
        interval=args.interval,
        start_offset=args.start_offset,
    )

    # Show preview
    print_start_list(riders)
    print_summary(riders)

    # Write output
    if not args.dry_run:
        output_path = Path(args.output_csv) if args.output_csv else input_path.with_name("tt-start-list.csv")
        write_start_list(output_path, riders)
        print(f"\nStart list written to: {output_path}")
    else:
        print("\n(Dry run — no file written)")

    # Publish to GitHub Pages
    if args.publish:
        from timetrial.config.settings import load_config
        config = load_config()

        race_name = args.race_name
        event_info = args.event_info

        # Use config values if CLI flags weren't explicitly provided
        if race_name == parser.get_default("race_name") and config.race_title:
            race_name = config.race_title
        if event_info == parser.get_default("event_info") and config.event_info:
            event_info = config.event_info

        publish_start_list(
            riders,
            race_name=race_name,
            event_info=event_info,
            race_time=args.race_time,
        )


if __name__ == "__main__":
    main()
