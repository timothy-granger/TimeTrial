"""Tests for the registration import conversion tool."""

import csv
import textwrap
from pathlib import Path

import pytest

from timetrial.tools.registration_import import (
    CLUB_CATEGORIES,
    WINDOW_ORDER,
    Registration,
    build_start_list,
    parse_registrations,
    write_start_list,
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
        bibs = [r.bib_number for r in riders]
        assert bibs == ["1", "2", "3", "4", "5"]

    def test_custom_bib_range(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, bib_start=50, bib_end=100)
        assert riders[0].bib_number == "50"
        assert riders[-1].bib_number == "54"

    def test_positions_are_sequential(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, interval=0.5, start_offset=0.5)
        positions = [r.start_position for r in riders]
        assert positions == [0.5, 1.0, 1.5, 2.0, 2.5]

    def test_custom_interval(self, sample_csv: Path):
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs, interval=1.0, start_offset=1.0)
        positions = [r.start_position for r in riders]
        assert positions == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_early_window_before_late(self, sample_csv: Path):
        """Riders requesting Early should come before Late."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        # Jones requested Late, should be last
        jones_idx = next(i for i, r in enumerate(riders) if r.last_name == "Jones")
        smith_idx = next(i for i, r in enumerate(riders) if r.last_name == "Smith")
        assert smith_idx < jones_idx

    def test_category_grouping_within_window(self, sample_csv: Path):
        """Within the same window, riders should be grouped by category order."""
        regs = parse_registrations(sample_csv)
        riders, _ec = build_start_list(regs)
        # All Early riders: Davis (Masters 60+), Smith (Merckx Men), Garcia (Merckx Women)
        early_riders = [r for r in riders if r.last_name in ("Davis", "Smith", "Garcia")]
        # Masters 60+ - Men is index 6, Merckx - Men is 10, Merckx - Women is 11
        assert early_riders[0].last_name == "Davis"   # Masters 60+ first
        assert early_riders[1].last_name == "Smith"    # Merckx Men next
        assert early_riders[2].last_name == "Garcia"   # Merckx Women last


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
        # Data rows
        assert len(lines) == 6  # header + 5 riders

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

        assert len(start_data.riders) == 5
        assert start_data.riders[0].bib_number == "1"
        assert start_data.riders[0].last_name == riders[0].last_name
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
