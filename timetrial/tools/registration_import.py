"""Convert Google Forms registration CSV into a TimeTrial start list.

Google Forms exports a CSV with columns:
    Timestamp, Last Name, First Name, Category, Preferred Start Window,
    Emergency Contact, Emergency Contact Phone

This tool reads that CSV, groups riders by preferred window then category,
assigns bib numbers and start positions (60-second spacing by default), and
writes the standard 7-column start list CSV the app expects.

Usage:
    python -m timetrial.tools.registration_import <input_csv> [output_csv]

    input_csv   Path to the Google Forms CSV export
    output_csv  Path for generated start list (default: tt-start-list.csv
                in the same directory as the input)

Options:
    --bib-start N       First bib number to assign (default: 1)
    --bib-end N         Last bib number available (default: 100)
    --interval M        Start interval in minutes (default: 1.0 = 60 sec)
    --start-offset M    First rider's start position in minutes
                        (default: same as --interval)
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

def _normalize_header(name: str) -> str:
    """Normalize a CSV header for flexible, order-independent matching.

    Lowercases, drops '#' characters, and collapses whitespace so Google
    Forms variants like ``Emergency Contact Phone #`` match the expected
    ``emergency contact phone`` (Google appends '#' to phone-number fields).
    """
    return " ".join(name.replace("#", " ").split()).lower()


class Registration:
    """One registration row from the Google Forms CSV."""

    __slots__ = (
        "last_name", "first_name", "category", "window",
        "emergency_contact", "emergency_phone", "timestamp",
    )

    def __init__(
        self, last: str, first: str, category: str, window: str,
        emergency_contact: str = "", emergency_phone: str = "",
        timestamp: datetime | None = None,
    ) -> None:
        self.last_name = last.strip()
        self.first_name = first.strip()
        self.category = category.strip()
        self.window = window.strip()
        self.emergency_contact = emergency_contact.strip()
        self.emergency_phone = emergency_phone.strip()
        self.timestamp = timestamp or datetime.min

    def __repr__(self) -> str:
        return (
            f"Registration({self.first_name} {self.last_name}, "
            f"{self.category}, {self.window}, "
            f"EC: {self.emergency_contact} {self.emergency_phone})"
        )


def parse_registrations(path: Path) -> list[Registration]:
    """Read a Google Forms CSV export and return Registration objects.

    Expected columns (by header name, order-independent):
        Timestamp          (ignored)
        Last Name
        First Name
        Category
        Preferred Start Window
        Emergency Contact       (optional)
        Emergency Contact Phone (optional)

    Raises ValueError on missing columns or empty required fields.
    """
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())

    # Normalize header names for flexible matching
    if reader.fieldnames is None:
        raise ValueError(f"Empty CSV file: {path}")

    field_map = {_normalize_header(f): f for f in reader.fieldnames}
    required = {
        "last name": "Last Name",
        "first name": "First Name",
        "category": "Category",
        "preferred start window": "Preferred Start Window",
    }
    optional = {
        "timestamp": "Timestamp",
        "emergency contact": "Emergency Contact",
        "emergency contact phone": "Emergency Contact Phone",
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

    # Resolve optional columns (may not exist in older CSVs)
    resolved_optional: dict[str, str | None] = {}
    for key, display in optional.items():
        resolved_optional[key] = field_map.get(key)

    registrations: list[Registration] = []
    for row_num, row in enumerate(reader, start=2):
        last = row[resolved["last name"]].strip()
        first = row[resolved["first name"]].strip()
        category = row[resolved["category"]].strip()
        window = row[resolved["preferred start window"]].strip()

        # Parse timestamp for registration-order priority
        ts_col = resolved_optional.get("timestamp")
        timestamp = datetime.min
        if ts_col and ts_col in row and row[ts_col].strip():
            try:
                timestamp = datetime.strptime(row[ts_col].strip(), "%m/%d/%Y %H:%M:%S")
            except ValueError:
                pass  # fall back to datetime.min

        ec_col = resolved_optional.get("emergency contact")
        ec_name = row[ec_col].strip() if ec_col and ec_col in row else ""
        ec_phone_col = resolved_optional.get("emergency contact phone")
        ec_phone = row[ec_phone_col].strip() if ec_phone_col and ec_phone_col in row else ""

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

        registrations.append(Registration(last, first, category, window, ec_name, ec_phone, timestamp))

    return registrations


def find_duplicate_registrations(
    registrations: list[Registration],
) -> list[list[Registration]]:
    """Group registrations that share the same (first, last) name.

    Returns a list of groups, each holding 2+ registrations with the same
    normalized name — a likely duplicate sign-up (e.g. a rider who registered
    twice). The tool never auto-removes these; a human reviews the warning and
    decides. Riders who merely share a last name (e.g. spouses) are NOT flagged
    because the first name is part of the key.
    """
    from collections import defaultdict

    groups: dict[tuple[str, str], list[Registration]] = defaultdict(list)
    for reg in registrations:
        key = (reg.first_name.strip().lower(), reg.last_name.strip().lower())
        groups[key].append(reg)
    return [g for g in groups.values() if len(g) > 1]


# ---------------------------------------------------------------------------
# Start list generation
# ---------------------------------------------------------------------------

def _sort_key(reg: Registration) -> tuple[int, datetime]:
    """Sort registrations by window preference, then registration timestamp."""
    window_rank = WINDOW_ORDER.get(reg.window, 999)
    return (window_rank, reg.timestamp)


# Each preferred window covers 15 minutes of wall clock (6:00-6:15, etc.).
WINDOW_DURATION_MINUTES = 15

WINDOW_NAMES = list(WINDOW_ORDER.keys())


def build_window_slots(
    interval: float, start_offset: float
) -> dict[str, tuple[float, int]]:
    """Return {window: (start_position, max_slots)} for the given interval.

    Each window spans WINDOW_DURATION_MINUTES of wall clock. The first window
    begins at ``start_offset``; each later window begins one duration later.
    The slot count is how many riders fit in a window at this interval, so it
    scales automatically with the spacing:

        30-sec spacing (interval=0.5, offset=0.5) → 30 slots/window at 0.5/15.5/30.5
        60-sec spacing (interval=1.0, offset=1.0) → 15 slots/window at 1.0/16.0/31.0
    """
    slots = max(1, round(WINDOW_DURATION_MINUTES / interval))
    return {
        name: (idx * WINDOW_DURATION_MINUTES + start_offset, slots)
        for idx, name in enumerate(WINDOW_NAMES)
    }


def build_start_list(
    registrations: list[Registration],
    bib_start: int = 1,
    bib_end: int = 100,
    interval: float = 1.0,
    start_offset: float | None = None,
    bib_by_slot: bool = False,
) -> tuple[list[Rider], dict[str, dict[str, str]]]:
    """Convert registrations into a sorted list of Riders with assigned bibs.

    Riders are placed into their preferred start window (Early/Middle/Late),
    ordered by registration timestamp (earliest first). If a window is full,
    the rider overflows to the next window; once every window is full, the
    remaining riders continue past the last window (e.g. past 6:45).

    Bib assignment depends on ``bib_by_slot``:
        False (default) — bibs run contiguously in start order (Race 1 style):
            the next rider always gets the next number regardless of gaps.
        True — a rider's bib is tied to their start-time slot: the slot at
            ``start_offset`` is ``bib_start`` and each later slot increments by
            one, so empty minutes between windows still consume bib numbers
            (e.g. a 6:16 rider becomes #45 when 6:01 is #30 at 60-sec spacing).

    ``interval`` is the spacing between riders in minutes (1.0 = 60 sec).
    ``start_offset`` is the first rider's position; it defaults to ``interval``
    so the first rider goes off one interval after the gun.

    Returns a tuple of (riders, emergency_contacts) where emergency_contacts
    maps bib number to {"name": ..., "phone": ...}.
    """
    if start_offset is None:
        start_offset = interval
    window_slots = build_window_slots(interval, start_offset)
    sorted_regs = sorted(registrations, key=_sort_key)

    available_bibs = bib_end - bib_start + 1
    if len(sorted_regs) > available_bibs:
        print(
            f"  Warning: {len(sorted_regs)} registrations but only "
            f"{available_bibs} bibs available ({bib_start}-{bib_end}). "
            f"Extra riders will get bibs beyond {bib_end}."
        )

    # Buckets for each window: list of registrations placed there
    window_buckets: dict[str, list[Registration]] = {w: [] for w in WINDOW_NAMES}

    for reg in sorted_regs:
        preferred = reg.window if reg.window in WINDOW_ORDER else WINDOW_NAMES[-1]
        placed = False

        # Try preferred window, then subsequent windows
        start_idx = WINDOW_NAMES.index(preferred)
        for idx in range(start_idx, len(WINDOW_NAMES)):
            window = WINDOW_NAMES[idx]
            _, max_slots = window_slots[window]
            if len(window_buckets[window]) < max_slots:
                window_buckets[window].append(reg)
                if idx != start_idx:
                    print(
                        f"  Note: {reg.first_name} {reg.last_name} bumped from "
                        f"{preferred} to {window} (window full)"
                    )
                placed = True
                break

        if not placed:
            # All windows full — append to last window beyond its capacity
            window_buckets[WINDOW_NAMES[-1]].append(reg)
            print(
                f"  Warning: {reg.first_name} {reg.last_name} placed in overflow "
                f"(all windows full)"
            )

    # Build riders in window order, filling gaps with placeholders
    riders: list[Rider] = []
    emergency_contacts: dict[str, dict[str, str]] = {}
    bib_counter = bib_start
    position = start_offset  # start at 0.5

    for window_idx, window in enumerate(WINDOW_NAMES):
        bucket = window_buckets[window]
        if not bucket:
            continue
        window_start, _ = window_slots[window]

        # Fill gap from current position to this window's start with placeholders
        while position < window_start:
            riders.append(Rider(
                bib_number="----",
                last_name="----",
                first_name="----",
                category="----",
                start_position=position,
            ))
            position += interval

        # Place real riders in this window
        for reg in bucket:
            if bib_by_slot:
                slot_index = round((position - start_offset) / interval)
                bib = str(bib_start + slot_index)
            else:
                bib = str(bib_counter)
            rider = Rider(
                bib_number=bib,
                last_name=reg.last_name,
                first_name=reg.first_name,
                category=reg.category,
                start_position=position,
            )
            riders.append(rider)
            if reg.emergency_contact or reg.emergency_phone:
                emergency_contacts[bib] = {
                    "name": reg.emergency_contact,
                    "phone": reg.emergency_phone,
                }
            bib_counter += 1
            position += interval

    return riders, emergency_contacts


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


def write_emergency_contacts(
    path: Path,
    riders: list[Rider],
    emergency_contacts: dict[str, dict[str, str]],
) -> None:
    """Write a LOCAL emergency-contact reference CSV for race-day officials.

    This file is for on-site use only and is NEVER published to the web.
    Columns: BIB, RIDER, CATEGORY, EMERGENCY_CONTACT, PHONE. Placeholder
    (filler) slots are skipped.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["BIB", "RIDER", "CATEGORY", "EMERGENCY_CONTACT", "PHONE"])
        for r in riders:
            if r.is_placeholder:
                continue
            ec = emergency_contacts.get(r.bib_number, {})
            writer.writerow([
                r.bib_number,
                f"{r.first_name} {r.last_name}".strip(),
                r.category,
                ec.get("name", ""),
                ec.get("phone", ""),
            ])


def print_start_list(riders: list[Rider]) -> None:
    """Print a formatted preview of the start list (skips placeholders)."""
    print(f"\n{'Bib':>4}  {'Last Name':<20} {'First Name':<15} {'Category':<25} {'Pos':>5}")
    print("-" * 75)
    prev_window = ""
    for r in riders:
        if r.is_placeholder:
            continue

        # Determine window from position
        if r.start_position <= 15.0:
            window = "Early (6:00 - 6:15)"
        elif r.start_position <= 30.0:
            window = "Middle (6:16 - 6:30)"
        else:
            window = "Late (6:31 - 6:45)"

        if window != prev_window:
            if prev_window:
                print()
            print(f"  --- {window} ---")
            prev_window = window

        pos = _format_position(r.start_position)
        print(f"{r.bib_number:>4}  {r.last_name:<20} {r.first_name:<15} {r.category:<25} {pos:>5}")


def print_emergency_contacts(
    riders: list[Rider],
    emergency_contacts: dict[str, dict[str, str]],
) -> None:
    """Print emergency contact info for all riders."""
    if not emergency_contacts:
        return
    print(f"\n{'Bib':>4}  {'Rider':<30} {'Emergency Contact':<25} {'Phone':<15}")
    print("-" * 78)
    for r in riders:
        ec = emergency_contacts.get(r.bib_number, {})
        ec_name = ec.get("name", "")
        ec_phone = ec.get("phone", "")
        if ec_name or ec_phone:
            print(
                f"{r.bib_number:>4}  {r.first_name + ' ' + r.last_name:<30} "
                f"{ec_name:<25} {ec_phone:<15}"
            )


def print_summary(riders: list[Rider]) -> None:
    """Print category and window distribution summary."""
    from collections import Counter

    real_riders = [r for r in riders if not r.is_placeholder]
    cat_counts: Counter[str] = Counter()
    for r in real_riders:
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

    placeholders = len(riders) - len(real_riders)
    print(f"\nTotal riders: {len(real_riders)}")
    print(f"Total slots: {len(riders)} ({placeholders} empty)")
    total_minutes = riders[-1].start_position if riders else 0
    print(f"Race duration: {total_minutes:.1f} minutes")
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
    emergency_contacts: dict[str, dict[str, str]] | None = None,
) -> None:
    """Write startlist.json to the GitHub Pages repo and push."""
    if not repo_path.exists():
        print(f"Error: repo not found at {repo_path}")
        sys.exit(1)

    ec = emergency_contacts or {}
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
            if not r.is_placeholder
        ],
        "emergency_contacts": {
            bib: {"name": info["name"], "phone": info["phone"]}
            for bib, info in ec.items()
        },
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
    parser.add_argument("--interval", type=float, default=1.0, help="Start interval in minutes (default: 1.0 = 60 sec)")
    parser.add_argument("--start-offset", type=float, default=None, help="First rider position (default: same as --interval)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write file")
    parser.add_argument("--publish", action="store_true", help="Publish start list to GitHub Pages")
    parser.add_argument("--race-name", default="Greenville Spinners Time Trial", help="Race name for web display")
    parser.add_argument("--event-info", default="", help="Event info (e.g. date)")
    parser.add_argument("--race-time", default="18:00", help="Race start time HH:MM (default: 18:00)")
    parser.add_argument("--emergency-csv", help="Write a LOCAL emergency-contact reference CSV for officials (never published)")
    parser.add_argument("--bib-by-slot", action="store_true", help="Bib number tracks the start-time slot (empty minutes consume numbers); default is contiguous per rider")

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

    # Warn about likely duplicate sign-ups (does not auto-remove — review first)
    duplicates = find_duplicate_registrations(registrations)
    if duplicates:
        print(f"\n  WARNING: {len(duplicates)} possible duplicate rider(s) -- review before publishing:")
        for group in duplicates:
            r = group[0]
            times = ", ".join(
                reg.timestamp.strftime("%m/%d %H:%M") if reg.timestamp != datetime.min else "?"
                for reg in group
            )
            print(f"    {r.first_name} {r.last_name} appears {len(group)}x (registered: {times})")

    # Build start list
    riders, emergency_contacts = build_start_list(
        registrations,
        bib_start=args.bib_start,
        bib_end=args.bib_end,
        interval=args.interval,
        start_offset=args.start_offset,
        bib_by_slot=args.bib_by_slot,
    )

    # Show preview
    print_start_list(riders)
    print_emergency_contacts(riders, emergency_contacts)
    print_summary(riders)

    # Write output
    if not args.dry_run:
        output_path = Path(args.output_csv) if args.output_csv else input_path.with_name("tt-start-list.csv")
        write_start_list(output_path, riders)
        print(f"\nStart list written to: {output_path}")
    else:
        print("\n(Dry run — no file written)")

    # Optional LOCAL emergency-contact sheet (officials only — never published)
    if args.emergency_csv and not args.dry_run:
        ec_path = Path(args.emergency_csv)
        write_emergency_contacts(ec_path, riders, emergency_contacts)
        print(f"Emergency contact sheet written to: {ec_path}")

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

        # Emergency contacts are intentionally NOT published: startlist.json
        # lives in a public repo. EC data stays local (see --emergency-csv).
        publish_start_list(
            riders,
            race_name=race_name,
            event_info=event_info,
            race_time=args.race_time,
        )


if __name__ == "__main__":
    main()
