"""Tests for the registration import conversion tool."""

import csv
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from timetrial.tools.registration_import import (
    CLUB_CATEGORIES,
    WINDOW_ORDER,
    Registration,
    build_start_list,
    build_window_slots,
    find_duplicate_registrations,
    parse_registrations,
    write_start_list,
    write_emergency_contacts,
    _format_start_time,
)
from timetrial.models.result import NO_RESULT_SENTINEL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a sample Google Forms CSV export."""
    csv_path = tmp_path / "registrations.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp", "First Name", "Last Name",
            "Category", "Preferred Start Window",
            "Emergency Contact", "Emergency Contact Phone"
        ])
        writer.writerow(["5/20/2026 9:00", "John", "Smith", "Merckx - Men", "Early (6:00 - 6:15)", "Jane Smith", "555-0101"])
        writer.writerow(["5/20/2026 9:05", "Sarah", "Jones", "Women (4/U)", "Late (6:31 - 6:45)", "Tom Jones", "555-0102"])
        writer.writerow(["5/20/2026 9:10", "Maria", "Garcia", "Merckx - Women", "Early (6:00 - 6:15)", "Luis Garcia", "555-0103"])
        writer.writerow(["5/20/2026 9:15", "Chris", "Brown", "Men (4/5/U)", "Middle (6:16 - 6:30)", "Pat Brown", "555-0104"])
        writer.writerow(["5/20/2026 9:20", "Robert", "Davis", "Masters 60+ - Men", "Early (6:00 - 6:15)", "Sue Davis", "555-0105"])
    return csv_path


@pytest.fixture
def sample_csv_no_ec(tmp_path: Path) -> Path:
    """Create a sample CSV without emergency contact columns (backward compat)."""
    csv_path = tmp_path / "registrations_old.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp", "Last Name", "First Name",
            "Category", "Preferred Start Window"
        ])
        writer.writerow(["5/20/2026 9:00", "Smith", "John", "Merckx - Men", "Early (6:00 - 6:15)"])
    return csv_path


@pytest.fixture
def utf8_bom_csv(tmp_path: Path) -> Path:
    """Create a CSV with UTF-8 BOM (common from Google Sheets)."""
    csv_path = tmp_path / "bom_registrations.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp", "Last Name", "First Name",
            "Category", "Preferred Start Window",
            "Emergency Contact", "Emergency Contact Phone"
        ])
        writer.writerow(["5/20/2026 9:00", "Miller", "James", "Men (P/1/2/3)", "Early (6:00 - 6:15)", "Ann Miller", "555-0200"])
    return csv_path


# ---------------------------------------------------------------------------
# Category list tests
# ---------------------------------------------------------------------------

class TestCategories:
    def test_category_count(self):
        assert len(CLUB_CATEGORIES) == 15

    def test_no_team_categories(self):
        for cat in CLUB_CATEGORIES:
            assert "Team" not in cat

    def test_masters_70_women_included(self):
        assert "Masters 70+ - Women" in CLUB_CATEGORIES

    def test_window_count(self):
        assert len(WINDOW_ORDER) == 3


# ---------------------------------------------------------------------------
# Parse tests
# ---------------------------------------------------------------------------

class TestParseRegistrations:
    def test_parse_valid_csv(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        assert len(regs) == 5

    def test_parse_fields(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        smith = regs[0]
        assert smith.last_name == "Smith"
        assert smith.first_name == "John"
        assert smith.category == "Merckx - Men"
        assert smith.window == "Early (6:00 - 6:15)"

    def test_parse_utf8_bom(self, utf8_bom_csv: Path):
        regs = parse_registrations(utf8_bom_csv)
        assert len(regs) == 1
        assert regs[0].last_name == "Miller"

    def test_parse_missing_column(self, tmp_path: Path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("Timestamp,Last Name,First Name\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Missing required column"):
            parse_registrations(csv_path)

    def test_parse_empty_csv(self, tmp_path: Path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="Empty CSV"):
            parse_registrations(csv_path)

    def test_skip_missing_name(self, tmp_path: Path):
        csv_path = tmp_path / "missing_name.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Last Name", "First Name", "Category", "Preferred Start Window"])
            writer.writerow(["5/20/2026", "", "John", "Merckx - Men", "Early (6:00 - 6:15)"])
            writer.writerow(["5/20/2026", "Smith", "Jane", "Merckx - Women", "Early (6:00 - 6:15)"])
        regs = parse_registrations(csv_path)
        assert len(regs) == 1
        assert regs[0].last_name == "Smith"

    def test_skip_missing_category(self, tmp_path: Path):
        csv_path = tmp_path / "missing_cat.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Last Name", "First Name", "Category", "Preferred Start Window"])
            writer.writerow(["5/20/2026", "Smith", "John", "", "Early (6:00 - 6:15)"])
        regs = parse_registrations(csv_path)
        assert len(regs) == 0


# ---------------------------------------------------------------------------
# Build start list tests
# ---------------------------------------------------------------------------

class TestBuildStartList:
    def test_bib_assignment(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, bib_start=1, bib_end=100)
        real_bibs = [r.bib_number for r in riders if not r.is_placeholder]
        assert real_bibs == ["1", "2", "3", "4", "5"]

    def test_custom_bib_range(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, bib_start=50, bib_end=100)
        real = [r for r in riders if not r.is_placeholder]
        assert real[0].bib_number == "50"
        assert real[-1].bib_number == "54"

    def test_positions_use_time_windows(self, sample_csv: Path):
        """Real riders are placed into their preferred time windows."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, interval=0.5)
        real_positions = [r.start_position for r in riders if not r.is_placeholder]
        # 3 Early (0.5, 1.0, 1.5), 1 Middle (15.5), 1 Late (30.5)
        assert real_positions == [0.5, 1.0, 1.5, 15.5, 30.5]

    def test_filler_records_bridge_windows(self, sample_csv: Path):
        """Placeholder fillers bridge the gap between windows."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, interval=0.5)
        # Positions should be continuous 0.5, 1.0, 1.5, 2.0, ..., 30.5
        positions = [r.start_position for r in riders]
        expected = [0.5 + i * 0.5 for i in range(len(riders))]
        assert positions == expected
        # Fillers should have bib "----"
        fillers = [r for r in riders if r.is_placeholder]
        assert len(fillers) > 0
        assert all(r.bib_number == "----" for r in fillers)

    def test_early_window_before_late(self, sample_csv: Path):
        """Riders requesting Early should come before Late."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        real = [r for r in riders if not r.is_placeholder]
        jones_idx = next(i for i, r in enumerate(real) if r.last_name == "Jones")
        smith_idx = next(i for i, r in enumerate(real) if r.last_name == "Smith")
        assert smith_idx < jones_idx

    def test_bib_by_slot(self, sample_csv: Path):
        """With bib_by_slot, a rider's bib tracks their start-time slot, so
        empty minutes between windows consume bib numbers."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, bib_start=30, interval=1.0, bib_by_slot=True)
        real = [(r.start_position, r.bib_number) for r in riders if not r.is_placeholder]
        # sample: 3 Early (pos 1,2,3), 1 Middle (pos 16), 1 Late (pos 31)
        # slot bibs: 30,31,32 then 30+15=45 then 30+30=60
        assert real == [(1.0, "30"), (2.0, "31"), (3.0, "32"), (16.0, "45"), (31.0, "60")]

    def test_bib_by_slot_ec_keyed_by_slot_bib(self, sample_csv: Path):
        """Emergency contacts are keyed by the slot-based bib number."""
        regs = parse_registrations(sample_csv)
        _riders, ec = build_start_list(regs, bib_start=30, interval=1.0, bib_by_slot=True)
        assert "45" in ec  # the 6:16 Middle rider
        assert "60" in ec  # the 6:31 Late rider

    def test_bib_contiguous_still_default(self, sample_csv: Path):
        """Default (no bib_by_slot) keeps contiguous bibs in start order."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, bib_start=30, interval=1.0)
        real = [r.bib_number for r in riders if not r.is_placeholder]
        assert real == ["30", "31", "32", "33", "34"]

    def test_registration_order_within_window(self, sample_csv: Path):
        """Within the same window, riders are ordered by registration timestamp."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        # All Early riders: Smith (9:00), Garcia (9:10), Davis (9:20) — by timestamp
        early_riders = [r for r in riders if r.last_name in ("Davis", "Smith", "Garcia")]
        assert early_riders[0].last_name == "Smith"    # registered first
        assert early_riders[1].last_name == "Garcia"   # registered second
        assert early_riders[2].last_name == "Davis"    # registered third


# ---------------------------------------------------------------------------
# Write start list tests
# ---------------------------------------------------------------------------

class TestWriteStartList:
    def _read_lines(self, path: Path) -> list[str]:
        """Read CSV and return non-empty lines."""
        text = path.read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip()]

    def test_output_format(self, sample_csv: Path, tmp_path: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        output = tmp_path / "tt-start-list.csv"
        write_start_list(output, riders)

        lines = self._read_lines(output)

        # Header
        assert lines[0].startswith("BIB_NUMBER")
        # Data rows: 5 real riders + fillers bridging windows
        real_lines = [l for l in lines[1:] if not l.startswith("----")]
        assert len(real_lines) == 5

    def test_output_has_seven_columns(self, sample_csv: Path, tmp_path: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        output = tmp_path / "tt-start-list.csv"
        write_start_list(output, riders)

        lines = self._read_lines(output)
        for line_no, line in enumerate(lines, start=1):
            if line_no == 1:
                continue  # skip header
            fields = line.split(",")
            assert len(fields) == 7, f"Line {line_no} has {len(fields)} fields: {line}"

    def test_output_has_sentinels(self, sample_csv: Path, tmp_path: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        output = tmp_path / "tt-start-list.csv"
        write_start_list(output, riders)

        lines = self._read_lines(output)
        fields = lines[1].split(",")
        assert fields[5] == NO_RESULT_SENTINEL
        assert fields[6] == NO_RESULT_SENTINEL

    def test_round_trip_with_import_service(self, sample_csv: Path, tmp_path: Path):
        """The output CSV should be importable by the existing ImportExportService."""
        from timetrial.services.import_export_service import ImportExportService
        from timetrial.config.settings import load_config

        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        output = tmp_path / "tt-start-list.csv"
        write_start_list(output, riders)

        config = load_config()
        svc = ImportExportService(config)
        start_data = svc.import_start_list(output)

        # Total includes fillers; filter to real riders
        real = [r for r in start_data.riders if not r.is_placeholder]
        assert len(real) == 5
        assert real[0].bib_number == "1"
        assert real[0].last_name == riders[0].last_name
        assert start_data.riders[0].category == riders[0].category


# ---------------------------------------------------------------------------
# Emergency contact tests
# ---------------------------------------------------------------------------

class TestEmergencyContacts:
    def test_parse_emergency_fields(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        smith = next(r for r in regs if r.last_name == "Smith")
        assert smith.emergency_contact == "Jane Smith"
        assert smith.emergency_phone == "555-0101"

    def test_emergency_contacts_in_build_result(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        riders, ec = build_start_list(regs)
        assert len(ec) == 5
        # Check first rider's emergency contact
        first_bib = riders[0].bib_number
        assert ec[first_bib]["name"] != ""
        assert ec[first_bib]["phone"] != ""

    def test_backward_compat_no_ec_columns(self, sample_csv_no_ec: Path):
        """Old CSVs without emergency contact columns should still work."""
        regs = parse_registrations(sample_csv_no_ec)
        assert len(regs) == 1
        assert regs[0].emergency_contact == ""
        assert regs[0].emergency_phone == ""

    def test_backward_compat_build(self, sample_csv_no_ec: Path):
        regs = parse_registrations(sample_csv_no_ec)
        riders, ec = build_start_list(regs)
        assert len(riders) == 1
        assert len(ec) == 0

    def test_phone_header_with_hash(self, tmp_path: Path):
        """Google Forms appends '#' to phone fields; the header must still match
        so phone numbers aren't silently dropped."""
        csv_path = tmp_path / "hash_header.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "First Name", "Last Name", "Category",
                "Preferred Start Window", "Emergency Contact",
                "Emergency Contact Phone #",
            ])
            writer.writerow([
                "5/20/2026 9:00", "John", "Smith", "Merckx - Men",
                "Early (6:00 - 6:15)", "Jane Smith", "555-0101",
            ])
        regs = parse_registrations(csv_path)
        assert len(regs) == 1
        assert regs[0].emergency_contact == "Jane Smith"
        assert regs[0].emergency_phone == "555-0101"


# ---------------------------------------------------------------------------
# Local emergency-contact sheet (officials only — never published)
# ---------------------------------------------------------------------------

class TestWriteEmergencyContacts:
    def test_contents(self, sample_csv: Path, tmp_path: Path):
        regs = parse_registrations(sample_csv)
        riders, ec = build_start_list(regs)
        out = tmp_path / "ec.csv"
        write_emergency_contacts(out, riders, ec)

        rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
        assert rows[0] == ["BIB", "RIDER", "CATEGORY", "EMERGENCY_CONTACT", "PHONE"]
        data = rows[1:]
        assert len(data) == 5  # 5 real riders, no placeholder rows
        first = data[0]
        assert first[0] == "1"
        assert "Smith" in first[1]
        assert first[3] == "Jane Smith"
        assert first[4] == "555-0101"

    def test_skips_placeholders(self, sample_csv: Path, tmp_path: Path):
        regs = parse_registrations(sample_csv)
        riders, ec = build_start_list(regs)
        out = tmp_path / "ec.csv"
        write_emergency_contacts(out, riders, ec)
        assert "----" not in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Duplicate detection tests
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def _csv(self, tmp_path: Path, rows: list[list[str]]) -> Path:
        csv_path = tmp_path / "dups.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "First Name", "Last Name", "Category",
                "Preferred Start Window", "Emergency Contact",
                "Emergency Contact Phone #",
            ])
            writer.writerows(rows)
        return csv_path

    def test_detects_same_name_twice(self, tmp_path: Path):
        path = self._csv(tmp_path, [
            ["6/23/2026 11:49", "Anna", "Tabor", "Juniors (F)", "Early (6:00 - 6:15)", "Neil Tabor", "555-1"],
            ["6/25/2026 7:26", "Anna", "Tabor", "Juniors (F)", "Early (6:00 - 6:15)", "Neil Tabor", "555-1"],
            ["6/24/2026 9:00", "Sammy", "Clary", "Merckx - Men", "Early (6:00 - 6:15)", "Ally", "555-2"],
        ])
        regs = parse_registrations(path)
        dups = find_duplicate_registrations(regs)
        assert len(dups) == 1
        assert len(dups[0]) == 2
        assert dups[0][0].first_name == "Anna"
        assert dups[0][0].last_name == "Tabor"

    def test_same_last_name_different_person_not_flagged(self, tmp_path: Path):
        """Spouses sharing a last name must NOT be flagged as duplicates."""
        path = self._csv(tmp_path, [
            ["6/24/2026 8:00", "Amanda", "Pospischil", "Women (4/U)", "Late (6:31 - 6:45)", "Robert", "555-1"],
            ["6/24/2026 16:54", "Robert", "Pospischil", "Masters 70+ - Men", "Early (6:00 - 6:15)", "Amanda", "555-2"],
        ])
        regs = parse_registrations(path)
        assert find_duplicate_registrations(regs) == []

    def test_case_and_whitespace_insensitive(self, tmp_path: Path):
        path = self._csv(tmp_path, [
            ["6/23/2026 11:49", "Brooke", "Tabor", "Juniors (F)", "Early (6:00 - 6:15)", "Neil", "555-1"],
            ["6/25/2026 7:26", "brooke ", " tabor", "Juniors (F)", "Early (6:00 - 6:15)", "Neil", "555-1"],
        ])
        regs = parse_registrations(path)
        assert len(find_duplicate_registrations(regs)) == 1

    def test_no_duplicates_clean_list(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        assert find_duplicate_registrations(regs) == []


# ---------------------------------------------------------------------------
# Start time formatting tests
# ---------------------------------------------------------------------------

class TestFormatStartTime:
    def test_first_position(self):
        # 0.5 min = 30 seconds after 18:00
        assert _format_start_time(0.5, "18:00") == "6:00:30 PM"

    def test_whole_minute(self):
        # 1.0 min = 60 seconds after 18:00
        assert _format_start_time(1.0, "18:00") == "6:01 PM"

    def test_one_and_half(self):
        assert _format_start_time(1.5, "18:00") == "6:01:30 PM"

    def test_ten_minutes(self):
        assert _format_start_time(10.0, "18:00") == "6:10 PM"

    def test_thirty_minutes(self):
        assert _format_start_time(30.0, "18:00") == "6:30 PM"

    def test_custom_race_time(self):
        assert _format_start_time(0.5, "17:30") == "5:30:30 PM"

    def test_am_race_time(self):
        assert _format_start_time(1.0, "08:00") == "8:01 AM"

    def test_noon_crossover(self):
        assert _format_start_time(1.0, "11:59") == "12:00 PM"

    def test_large_position(self):
        # 45 min after 18:00 = 18:45
        assert _format_start_time(45.0, "18:00") == "6:45 PM"


# ---------------------------------------------------------------------------
# Start interval tests (60-second spacing for 2026 races 2-4)
# ---------------------------------------------------------------------------

class TestIntervalConfig:
    """The start interval is configurable. Races 2-4 use 60-second spacing,
    which halves each window's capacity (15 slots instead of 30) and pushes
    overflow riders past 6:45 instead of bumping them between windows."""

    def _regs(self, count: int, window: str, category: str = "Merckx - Men"):
        """Build `count` registrations in one window with increasing timestamps."""
        base = datetime(2026, 6, 1, 9, 0, 0)
        return [
            Registration(
                f"Last{i:02d}", f"First{i:02d}", category, window,
                timestamp=base + timedelta(seconds=i),
            )
            for i in range(count)
        ]

    def test_window_slots_thirty_second_unchanged(self):
        """30-second spacing keeps the original 30-slot windows (regression)."""
        early, middle, late = list(WINDOW_ORDER)
        slots = build_window_slots(interval=0.5, start_offset=0.5)
        assert slots[early] == (0.5, 30)
        assert slots[middle] == (15.5, 30)
        assert slots[late] == (30.5, 30)

    def test_window_slots_one_minute(self):
        """60-second spacing gives 15 slots per window at positions 1/16/31."""
        early, middle, late = list(WINDOW_ORDER)
        slots = build_window_slots(interval=1.0, start_offset=1.0)
        assert slots[early] == (1.0, 15)
        assert slots[middle] == (16.0, 15)
        assert slots[late] == (31.0, 15)

    def test_default_interval_is_one_minute(self, sample_csv: Path):
        """The first rider goes off at 6:01 (one 60-second interval after the gun)."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        first_real = next(r for r in riders if not r.is_placeholder)
        assert first_real.start_position == 1.0

    def test_one_minute_positions(self, sample_csv: Path):
        """At 60-second spacing the sample's 3 Early/1 Middle/1 Late map to 1/2/3, 16, 31."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, interval=1.0)
        real = [r.start_position for r in riders if not r.is_placeholder]
        assert real == [1.0, 2.0, 3.0, 16.0, 31.0]

    def test_window_holds_15_then_bumps_to_next(self):
        """The 16th Early rider bumps into Middle (6:16) once Early's 15 slots fill."""
        early = list(WINDOW_ORDER)[0]
        regs = self._regs(16, early)
        riders, _ec = build_start_list(regs, interval=1.0)
        real = [r.start_position for r in riders if not r.is_placeholder]
        assert real == [float(i) for i in range(1, 17)]

    def test_overflow_runs_past_645(self):
        """When all windows fill, extra riders continue past 6:45 instead of stopping."""
        late = list(WINDOW_ORDER)[2]
        regs = self._regs(46, late)
        riders, _ec = build_start_list(regs, interval=1.0)
        real = [r.start_position for r in riders if not r.is_placeholder]
        assert real[0] == 31.0
        assert any(p > 45.0 for p in real)
        assert real[-1] == 76.0
