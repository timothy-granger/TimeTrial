"""Bulk import tool — scan distro/, parse CSVs, produce review files, load into DB.

Usage:
    python -m timetrial.tools.bulk_import scan          # Scan and produce review files
    python -m timetrial.tools.bulk_import import         # Import using approved mappings
    python -m timetrial.tools.bulk_import query <name>   # Quick rider lookup
"""

from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from timetrial.config.settings import load_config
from timetrial.models.result import NO_RESULT_SENTINEL
from timetrial.services.import_export_service import ImportExportService
from timetrial.services.history_schema import HISTORY_SCHEMA


# ---------------------------------------------------------------------------
# Event map: folder name → (date_str, preferred CSV file pattern)
# Best file per event, preferring "final" or "results" versions
# ---------------------------------------------------------------------------

EVENT_MAP: list[dict] = [
    # 2017
    {"folder": "Backup", "date": "2017-07-20", "file": "official-07-20-2017-tt-start-list.csv", "type": "start"},
    {"folder": "Backup", "date": "2017-08-24", "file": "final-08-24-17-tt-start-list.csv", "type": "start"},
    {"folder": "Backup", "date": "2017-09-24", "file": "9-24-2017-tt-finish-list.csv", "type": "finish"},
    # 2018
    {"folder": "May 2018", "date": "2018-05-03", "file": "05-03-2018-final-tt-start-list.csv", "type": "start"},
    {"folder": "June 2018", "date": "2018-06-27", "file": "2018-june-tt-finish-list.csv", "type": "finish"},
    {"folder": "July 2018", "date": "2018-07-19", "file": "tt-start-list-final.csv", "type": "start"},
    {"folder": "August 2018", "date": "2018-08-23", "file": "tt-start-list-final.csv", "type": "start"},
    {"folder": "SC-State-2018", "date": "2018-09-15", "file": "tt-finish-list.csv", "type": "finish"},
    # 2019
    {"folder": "July 2019", "date": "2019-07-11", "file": "tt-start-list-results.csv", "type": "start"},
    {"folder": "August 2019", "date": "2019-08-22", "file": "tt-start-list-with-results.csv", "type": "start"},
    # 2020
    {"folder": "June 2020", "date": "2020-06-25", "file": "tt-start-list-results.official.csv", "type": "start"},
    {"folder": "July 2020", "date": "2020-07-16", "file": "tt-start-list-final-results.csv", "type": "start"},
    {"folder": "August 2020", "date": "2020-08-06", "file": "tt-start-list.csv", "type": "start"},
    # 2021
    {"folder": "2021.May", "date": "2021-05-13", "file": "tt-start-list.final.csv", "type": "start"},
    {"folder": "June.2021", "date": "2021-06-10", "file": "2021.june.final.tt-start-list.csv", "type": "start"},
    {"folder": "July 2021", "date": "2021-07-15", "file": "tt-start-list-july.csv", "type": "start"},
    {"folder": "August 2021", "date": "2021-08-19", "file": "tt-start-list.results.csv", "type": "start"},
    # 2022
    {"folder": "2022.May.05", "date": "2022-05-05", "file": "tt-start-list.csv", "type": "start"},
    {"folder": "2022.June.30", "date": "2022-06-30", "file": "tt-finish-list.csv", "type": "finish"},
    {"folder": "2022.july.28", "date": "2022-07-28", "file": "tt-start-list.results.csv", "type": "start"},
    {"folder": "2022.august.18", "date": "2022-08-18", "file": "tt-start-list.result.csv", "type": "start"},
    # 2023
    {"folder": "2023.may.11", "date": "2023-05-11", "file": "tt-start-list.results.csv", "type": "start"},
    {"folder": "2023.June.15", "date": "2023-06-15", "file": "tt-start-list.final.csv", "type": "start"},
    {"folder": "2023.July.27", "date": "2023-07-27", "file": "tt-start-list.final.csv", "type": "start"},
]


# ---------------------------------------------------------------------------
# Scan: extract all names and categories, produce review files
# ---------------------------------------------------------------------------

def scan(distro_path: Path, output_dir: Path) -> None:
    """Scan all events, extract raw data, produce review CSVs."""
    config = load_config(user_path=Path("/nonexistent"))
    io_svc = ImportExportService(config)

    all_names: dict[tuple[str, str], int] = defaultdict(int)  # (first, last) → count
    all_categories: dict[str, int] = defaultdict(int)  # category → count
    events_found: list[dict] = []
    errors: list[str] = []

    print(f"Scanning {len(EVENT_MAP)} events in {distro_path}...\n")

    for event in EVENT_MAP:
        folder = distro_path / event["folder"]
        csv_file = folder / event["file"]

        if not csv_file.exists():
            errors.append(f"  MISSING: {csv_file}")
            continue

        try:
            if event["type"] == "start":
                data = io_svc.import_start_list(csv_file)
                riders_with_results = [
                    (r, data.results.get(r.bib_number, NO_RESULT_SENTINEL))
                    for r in data.riders
                    if not r.is_placeholder and r.category != "----"
                    and data.results.get(r.bib_number, NO_RESULT_SENTINEL) != NO_RESULT_SENTINEL
                ]
            else:
                fdata = io_svc.import_finish_list(csv_file)
                riders_with_results = []
                for bib, last, first, cat, finish, result in fdata.rows:
                    if bib and bib != "----" and cat != "----" and result and result != NO_RESULT_SENTINEL:
                        # Create a pseudo-rider for name tracking
                        from timetrial.models.rider import Rider
                        r = Rider(bib, last, first, cat, 0.0)
                        riders_with_results.append((r, result))

            result_count = len(riders_with_results)
            events_found.append({
                "date": event["date"],
                "folder": event["folder"],
                "file": event["file"],
                "results": result_count,
            })

            for rider, result in riders_with_results:
                first = _clean_name(rider.first_name)
                last = _clean_name(rider.last_name)
                cat = rider.category.strip()
                all_names[(first, last)] += 1
                all_categories[cat] += 1

            print(f"  {event['date']}  {event['folder']:<25s}  {result_count:3d} results")

        except Exception as e:
            errors.append(f"  ERROR: {csv_file}: {e}")

    # -- Write review files --
    output_dir.mkdir(parents=True, exist_ok=True)

    # Events summary
    events_file = output_dir / "01_events_found.csv"
    with open(events_file, "w") as f:
        f.write("date,folder,file,results\n")
        for ev in sorted(events_found, key=lambda e: e["date"]):
            f.write(f"{ev['date']},{ev['folder']},{ev['file']},{ev['results']}\n")

    # All unique names with occurrence count
    names_file = output_dir / "02_all_names.csv"
    with open(names_file, "w") as f:
        f.write("first_name,last_name,appearances,canonical_first,canonical_last\n")
        for (first, last), count in sorted(all_names.items(), key=lambda x: (x[0][1].lower(), x[0][0].lower())):
            f.write(f"{first},{last},{count},{first},{last}\n")

    # All unique categories with count
    cats_file = output_dir / "03_all_categories.csv"
    with open(cats_file, "w") as f:
        f.write("raw_category,appearances,canonical_category\n")
        for cat, count in sorted(all_categories.items(), key=lambda x: x[0].lower()):
            canonical = _suggest_canonical_category(cat)
            f.write(f"{cat},{count},{canonical}\n")

    # Possible duplicate names (fuzzy matches)
    dupes_file = output_dir / "04_possible_duplicate_names.csv"
    name_list = sorted(all_names.keys(), key=lambda x: (x[1].lower(), x[0].lower()))
    with open(dupes_file, "w") as f:
        f.write("name_a,name_b,reason\n")
        for i, (first_a, last_a) in enumerate(name_list):
            for first_b, last_b in name_list[i + 1:]:
                reason = _check_duplicate(first_a, last_a, first_b, last_b)
                if reason:
                    f.write(f"{first_a} {last_a},{first_b} {last_b},{reason}\n")

    # Errors
    if errors:
        err_file = output_dir / "05_errors.txt"
        with open(err_file, "w") as f:
            f.write("\n".join(errors))

    print(f"\n{'=' * 60}")
    print(f"Events found:      {len(events_found)}")
    print(f"Unique riders:     {len(all_names)}")
    print(f"Unique categories: {len(all_categories)}")
    print(f"Errors:            {len(errors)}")
    print(f"\nReview files written to: {output_dir}")
    print(f"  {events_file.name}")
    print(f"  {names_file.name}")
    print(f"  {cats_file.name}")
    print(f"  {dupes_file.name}")
    if errors:
        print(f"  05_errors.txt")
    print(f"\nNext steps:")
    print(f"  1. Review 02_all_names.csv — edit canonical_first/canonical_last columns to fix typos")
    print(f"  2. Review 03_all_categories.csv — edit canonical_category column to normalize categories")
    print(f"  3. Review 04_possible_duplicate_names.csv — merge entries in 02_all_names.csv if needed")
    print(f"  4. Run: python -m timetrial.tools.bulk_import import")


# ---------------------------------------------------------------------------
# Import: load approved mappings + race data into DB
# ---------------------------------------------------------------------------

def do_import(distro_path: Path, review_dir: Path, db_path: Path) -> None:
    """Import all events into the history DB using approved mappings."""
    config = load_config(user_path=Path("/nonexistent"))
    io_svc = ImportExportService(config)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(HISTORY_SCHEMA)
    conn.commit()

    # Load name mappings
    name_map = _load_name_map(review_dir / "02_all_names.csv")
    cat_map = _load_category_map(review_dir / "03_all_categories.csv")

    # Save mappings to DB
    conn.executemany(
        "INSERT OR REPLACE INTO name_map (raw_first, raw_last, canonical_first, canonical_last) VALUES (?,?,?,?)",
        [(rf, rl, cf, cl) for (rf, rl), (cf, cl) in name_map.items()],
    )
    conn.executemany(
        "INSERT OR REPLACE INTO category_map (raw_name, canonical_name) VALUES (?,?)",
        list(cat_map.items()),
    )
    conn.commit()

    total_results = 0

    for event in EVENT_MAP:
        folder = distro_path / event["folder"]
        csv_file = folder / event["file"]

        if not csv_file.exists():
            continue

        try:
            # Parse race data
            if event["type"] == "start":
                data = io_svc.import_start_list(csv_file)
                raw_riders = [
                    (r, data.finish_times.get(r.bib_number, NO_RESULT_SENTINEL),
                     data.results.get(r.bib_number, NO_RESULT_SENTINEL))
                    for r in data.riders
                    if not r.is_placeholder and r.category != "----"
                ]
            else:
                fdata = io_svc.import_finish_list(csv_file)
                raw_riders = []
                for bib, last, first, cat, finish, result in fdata.rows:
                    if bib and bib != "----" and cat != "----":
                        from timetrial.models.rider import Rider
                        r = Rider(bib, last, first, cat, 0.0)
                        raw_riders.append((r, finish, result))

            # Create event
            cur = conn.execute(
                "INSERT OR IGNORE INTO race_events (event_date, source_file) VALUES (?, ?)",
                (event["date"], str(csv_file)),
            )
            conn.commit()

            # Get event_id (may already exist if re-running)
            cur = conn.execute(
                "SELECT event_id FROM race_events WHERE event_date = ?", (event["date"],)
            )
            event_id = cur.fetchone()[0]

            # Clear previous data for this event (idempotent re-import)
            conn.execute("DELETE FROM race_results WHERE event_id = ?", (event_id,))
            conn.execute("DELETE FROM race_entries WHERE event_id = ?", (event_id,))
            conn.commit()

            event_results = 0

            for rider, finish_str, result_str in raw_riders:
                # Normalize name
                raw_first = _clean_name(rider.first_name)
                raw_last = _clean_name(rider.last_name)
                canon_first, canon_last = name_map.get(
                    (raw_first, raw_last), (raw_first, raw_last)
                )

                # Normalize category
                raw_cat = rider.category.strip()
                canon_cat = cat_map.get(raw_cat, raw_cat)

                # Get or create master rider
                rider_id = _get_or_create_rider(conn, canon_first, canon_last)

                # Create entry
                cur = conn.execute(
                    "INSERT OR IGNORE INTO race_entries "
                    "(event_id, rider_id, bib_number, category, start_position) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (event_id, rider_id, rider.bib_number, canon_cat, rider.start_position),
                )
                conn.commit()

                cur = conn.execute(
                    "SELECT entry_id FROM race_entries WHERE event_id=? AND rider_id=?",
                    (event_id, rider_id),
                )
                entry_id = cur.fetchone()[0]

                # Create result if available
                if result_str and result_str != NO_RESULT_SENTINEL:
                    result_ms = _parse_result_ms(result_str)
                    conn.execute(
                        "INSERT OR REPLACE INTO race_results "
                        "(event_id, entry_id, rider_id, finish_time_str, result_time_str, "
                        "result_ms, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (event_id, entry_id, rider_id, finish_str, result_str,
                         result_ms, canon_cat),
                    )
                    event_results += 1

            conn.commit()

            # Calculate placements for this event
            _calculate_placements(conn, event_id, set(config.junior_categories))

            total_results += event_results
            print(f"  {event['date']}  {event_results:3d} results imported")

        except Exception as e:
            print(f"  ERROR {event['date']}: {e}")

    conn.commit()
    conn.close()

    print(f"\nImport complete: {total_results} total results across {len(EVENT_MAP)} events")
    print(f"Database: {db_path}")


# ---------------------------------------------------------------------------
# Query: quick rider lookup
# ---------------------------------------------------------------------------

def query_rider(db_path: Path, search: str) -> None:
    """Search for a rider and show their history."""
    conn = sqlite3.connect(str(db_path))

    cur = conn.execute(
        "SELECT rider_id, first_name, last_name FROM riders_master "
        "WHERE first_name || ' ' || last_name LIKE ? "
        "ORDER BY last_name, first_name",
        (f"%{search}%",),
    )
    riders = cur.fetchall()

    if not riders:
        print(f"No riders found matching '{search}'")
        conn.close()
        return

    for rider_id, first, last in riders:
        print(f"\n{'=' * 60}")
        print(f"  {first} {last}")
        print(f"{'=' * 60}")

        cur = conn.execute(
            "SELECT re.event_date, rr.category, rr.result_time_str, "
            "rr.category_place, rr.overall_place "
            "FROM race_results rr "
            "JOIN race_events re ON re.event_id = rr.event_id "
            "WHERE rr.rider_id = ? "
            "ORDER BY re.event_date",
            (rider_id,),
        )

        print(f"  {'Date':<12s}  {'Category':<25s}  {'Time':<14s}  {'Cat':>4s}  {'Ovr':>4s}")
        print(f"  {'-' * 12}  {'-' * 25}  {'-' * 14}  {'-' * 4}  {'-' * 4}")

        for date, cat, result, cat_place, ovr_place in cur.fetchall():
            cp = str(cat_place) if cat_place else "-"
            op = str(ovr_place) if ovr_place else "-"
            print(f"  {date:<12s}  {cat:<25s}  {result:<14s}  {cp:>4s}  {op:>4s}")

    # Personal bests
    print(f"\n  Personal Bests:")
    for rider_id, first, last in riders:
        cur = conn.execute(
            "SELECT category, MIN(result_ms) as best_ms, result_time_str, re.event_date "
            "FROM race_results rr "
            "JOIN race_events re ON re.event_id = rr.event_id "
            "WHERE rr.rider_id = ? "
            "GROUP BY category "
            "ORDER BY category",
            (rider_id,),
        )
        for cat, best_ms, best_time, date in cur.fetchall():
            print(f"    {cat:<25s}  {best_time}  ({date})")

    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_name(name: str) -> str:
    """Strip whitespace and normalize spacing."""
    return " ".join(name.strip().split())


def _suggest_canonical_category(cat: str) -> str:
    """Suggest a canonical category name based on common variations."""
    c = cat.strip()
    # Normalize spacing around hyphens
    c = re.sub(r'\s*-\s*', ' - ', c)
    # Common fixes
    c = c.replace("Master ", "Masters ")
    if c.startswith("Masters") and "+" in c and " - " not in c:
        c = c.replace("+", "+ -")
    return c


def _check_duplicate(first_a: str, last_a: str, first_b: str, last_b: str) -> str | None:
    """Check if two names might be the same person. Returns reason or None."""
    # Same last name, similar first name
    if last_a.lower() == last_b.lower():
        if first_a.lower() == first_b.lower():
            return "exact match (case diff)"
        if first_a.lower().startswith(first_b.lower()[:3]) or first_b.lower().startswith(first_a.lower()[:3]):
            return f"same last, similar first"
    # Trailing space artifacts
    if last_a.lower().strip() == last_b.lower().strip() and first_a.lower().strip() == first_b.lower().strip():
        return "whitespace difference"
    return None


def _load_name_map(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """Load name mappings from the reviewed CSV."""
    mapping: dict[tuple[str, str], tuple[str, str]] = {}
    if not path.exists():
        return mapping

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line_no == 1:
            continue  # header
        parts = line.split(",")
        if len(parts) >= 5:
            raw_first = parts[0].strip()
            raw_last = parts[1].strip()
            canon_first = parts[3].strip()
            canon_last = parts[4].strip()
            mapping[(raw_first, raw_last)] = (canon_first, canon_last)

    return mapping


def _load_category_map(path: Path) -> dict[str, str]:
    """Load category mappings from the reviewed CSV."""
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line_no == 1:
            continue  # header
        parts = line.split(",")
        if len(parts) >= 3:
            raw = parts[0].strip()
            canonical = parts[2].strip()
            mapping[raw] = canonical

    return mapping


def _get_or_create_rider(conn: sqlite3.Connection, first: str, last: str) -> int:
    """Get or create a master rider record."""
    cur = conn.execute(
        "SELECT rider_id FROM riders_master WHERE first_name=? AND last_name=?",
        (first, last),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur = conn.execute(
        "INSERT INTO riders_master (first_name, last_name) VALUES (?, ?)",
        (first, last),
    )
    conn.commit()
    return cur.lastrowid


def _parse_result_ms(result_str: str) -> int:
    """Parse 'hh:mm:ss.zzz' to milliseconds."""
    try:
        parts = result_str.split(".")
        base = parts[0]
        ms_str = (parts[1] if len(parts) > 1 else "000").ljust(3, "0")[:3]
        t = base.split(":")
        return (int(t[0]) * 3600 + int(t[1]) * 60 + int(t[2])) * 1000 + int(ms_str)
    except (ValueError, IndexError):
        return 0


def _calculate_placements(conn: sqlite3.Connection, event_id: int, junior_cats: set[str]) -> None:
    """Calculate category_place and overall_place for all results in an event."""
    # Category placements
    cur = conn.execute(
        "SELECT result_id, category, result_ms FROM race_results "
        "WHERE event_id = ? ORDER BY category, result_ms",
        (event_id,),
    )
    rows = cur.fetchall()

    current_cat = ""
    place = 0
    for result_id, category, result_ms in rows:
        if category != current_cat:
            current_cat = category
            place = 1
        else:
            place += 1
        conn.execute(
            "UPDATE race_results SET category_place = ? WHERE result_id = ?",
            (place, result_id),
        )

    # Overall placements (exclude juniors)
    cur = conn.execute(
        "SELECT result_id, category FROM race_results "
        "WHERE event_id = ? ORDER BY result_ms",
        (event_id,),
    )
    overall_place = 0
    for result_id, category in cur.fetchall():
        if category not in junior_cats:
            overall_place += 1
            conn.execute(
                "UPDATE race_results SET overall_place = ? WHERE result_id = ?",
                (overall_place, result_id),
            )

    conn.commit()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    distro_path = Path("D:/TimeTrial_Refactor/distro")
    review_dir = Path("D:/TimeTrial_Refactor/import_review")
    db_path = Path.home() / ".timetrial" / "history.db"

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "scan":
        scan(distro_path, review_dir)
    elif cmd == "import":
        do_import(distro_path, review_dir, db_path)
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: python -m timetrial.tools.bulk_import query <name>")
            return
        search = " ".join(sys.argv[2:])
        query_rider(db_path, search)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
