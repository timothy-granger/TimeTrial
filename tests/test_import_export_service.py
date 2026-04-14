"""Tests for ImportExportService — including round-trips against historical data."""

from pathlib import Path

import pytest

from timetrial.config.settings import load_config
from timetrial.models.rider import Rider
from timetrial.models.result import NO_RESULT_SENTINEL
from timetrial.models.series import SeriesEntry
from timetrial.services.import_export_service import (
    ImportExportService,
    StartListData,
    FinishListData,
    _format_position,
)

DISTRO = Path(__file__).parent.parent / "distro"


@pytest.fixture
def svc() -> ImportExportService:
    config = load_config(user_path=Path("/nonexistent"))
    return ImportExportService(config)


# ---------------------------------------------------------------------------
# Start List
# ---------------------------------------------------------------------------

class TestImportStartList:
    def test_basic_import(self, svc, tmp_path):
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT\r\n"
            "1,Smith,John,Men (4/5/U),0.5,--:--:--.---,--:--:--.---\r\n"
            "2,Jones,Jane,Women (P/1/2/3),1,18:24:22.492,00:23:22.492\r\n"
        )
        f = tmp_path / "start.csv"
        f.write_text(csv_content, encoding="utf-8")

        data = svc.import_start_list(f)
        assert len(data.riders) == 2

        assert data.riders[0].bib_number == "1"
        assert data.riders[0].last_name == "Smith"
        assert data.riders[0].start_position == 0.5

        assert data.riders[1].start_position == 1.0
        assert data.finish_times["2"] == "18:24:22.492"
        assert data.results["2"] == "00:23:22.492"

    def test_placeholder_rider(self, svc, tmp_path):
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT\r\n"
            "----,----,----,----,3.5,--:--:--.---,--:--:--.---\r\n"
        )
        f = tmp_path / "start.csv"
        f.write_text(csv_content, encoding="utf-8")

        data = svc.import_start_list(f)
        assert len(data.riders) == 1
        assert data.riders[0].is_placeholder

    def test_wrong_column_count_raises(self, svc, tmp_path):
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME\r\n"
            "1,Smith,John\r\n"
        )
        f = tmp_path / "start.csv"
        f.write_text(csv_content, encoding="utf-8")

        with pytest.raises(ValueError, match="expected 7 fields"):
            svc.import_start_list(f)

    def test_invalid_position_raises(self, svc, tmp_path):
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT\r\n"
            "1,Smith,John,Cat,abc,--:--:--.---,--:--:--.---\r\n"
        )
        f = tmp_path / "start.csv"
        f.write_text(csv_content, encoding="utf-8")

        with pytest.raises(ValueError, match="invalid start position"):
            svc.import_start_list(f)

    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_historical_2022_july(self, svc):
        data = svc.import_start_list(DISTRO / "2022.july.28" / "tt-start-list.csv")
        assert len(data.riders) > 0
        # All riders should have valid float positions
        for rider in data.riders:
            assert isinstance(rider.start_position, float)
            assert rider.start_position >= 0

    @pytest.mark.skipif(not (DISTRO / "2023.June.15").exists(), reason="distro data not present")
    def test_historical_2023_june(self, svc):
        data = svc.import_start_list(DISTRO / "2023.June.15" / "tt-start-list.csv")
        assert len(data.riders) > 0
        # Should have a mix of categories
        categories = {r.category for r in data.riders if not r.is_placeholder}
        assert len(categories) > 1


class TestExportStartList:
    def test_round_trip(self, svc, tmp_path):
        riders = [
            Rider("1", "Smith", "John", "Men (4/5/U)", 0.5),
            Rider("2", "Jones", "Jane", "Women (P/1/2/3)", 1.0),
            Rider("----", "----", "----", "----", 1.5),
        ]
        finish_times = {"2": "18:24:22.492"}
        results = {"2": "00:23:22.492"}

        f = tmp_path / "start.csv"
        svc.export_start_list(f, riders, finish_times, results)

        # Re-import
        data = svc.import_start_list(f)
        assert len(data.riders) == 3
        assert data.riders[0].bib_number == "1"
        assert data.riders[0].start_position == 0.5
        assert data.finish_times["1"] == NO_RESULT_SENTINEL  # default
        assert data.finish_times["2"] == "18:24:22.492"
        assert data.results["2"] == "00:23:22.492"
        assert data.riders[2].is_placeholder

    def test_crlf_line_endings(self, svc, tmp_path):
        f = tmp_path / "start.csv"
        svc.export_start_list(f, [Rider("1", "A", "B", "C", 1.0)])
        raw = f.read_bytes()
        assert b"\r\n" in raw

    def test_position_formatting(self, svc, tmp_path):
        riders = [
            Rider("1", "A", "B", "C", 1.0),   # should be "1"
            Rider("2", "D", "E", "F", 0.5),   # should be "0.5"
            Rider("3", "G", "H", "I", 1.5),   # should be "1.5"
        ]
        f = tmp_path / "start.csv"
        svc.export_start_list(f, riders)
        content = f.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        assert ",1," in lines[1]     # whole number
        assert ",0.5," in lines[2]   # half
        assert ",1.5," in lines[3]   # one-and-a-half


# ---------------------------------------------------------------------------
# Finish List
# ---------------------------------------------------------------------------

class TestImportFinishList:
    def test_basic_import(self, svc, tmp_path):
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, FINISH_TIME, RESULT\r\n"
            "4,Flynn,Ricky,Men (P/1/2/3),18:24:13.564,00:22:13.297\r\n"
        )
        f = tmp_path / "finish.csv"
        f.write_text(csv_content, encoding="utf-8")

        data = svc.import_finish_list(f)
        assert len(data.rows) == 1
        bib, last, first, cat, finish, result = data.rows[0]
        assert bib == "4"
        assert last == "Flynn"
        assert finish == "18:24:13.564"
        assert result == "00:22:13.297"

    def test_finish_time_padding(self, svc, tmp_path):
        """Legacy rule: if finish time < 12 chars, append '0'."""
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, FINISH_TIME, RESULT\r\n"
            "1,Smith,John,Cat,18:24:13.56,00:22:13.297\r\n"
        )
        f = tmp_path / "finish.csv"
        f.write_text(csv_content, encoding="utf-8")

        data = svc.import_finish_list(f)
        assert data.rows[0][4] == "18:24:13.560"  # padded

    def test_sentinel_not_padded(self, svc, tmp_path):
        """The no-result sentinel should not be padded."""
        csv_content = (
            "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, FINISH_TIME, RESULT\r\n"
            "1,Smith,John,Cat,--:--:--.---,--:--:--.---\r\n"
        )
        f = tmp_path / "finish.csv"
        f.write_text(csv_content, encoding="utf-8")

        data = svc.import_finish_list(f)
        assert data.rows[0][4] == NO_RESULT_SENTINEL

    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_historical_2022_july(self, svc):
        data = svc.import_finish_list(DISTRO / "2022.july.28" / "tt-finish-list.csv")
        assert len(data.rows) > 0
        for row in data.rows:
            assert len(row) == 6


class TestExportFinishList:
    def test_round_trip(self, svc, tmp_path):
        rows = [
            ("4", "Flynn", "Ricky", "Men (P/1/2/3)", "18:24:13.564", "00:22:13.297"),
            ("1", "Smith", "John", "Men (4/5/U)", "18:25:00.100", "00:24:30.100"),
        ]
        f = tmp_path / "finish.csv"
        svc.export_finish_list(f, rows)

        data = svc.import_finish_list(f)
        assert len(data.rows) == 2
        assert data.rows[0][0] == "4"
        assert data.rows[1][4] == "18:25:00.100"


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------

class TestImportSeries:
    def test_4_column_format(self, svc, tmp_path):
        """App's own format: FIRST_NAME, LAST_NAME, CATEGORY, POINTS."""
        csv_content = (
            "FIRST_NAME,LAST_NAME,CATEGORY,POINTS\r\n"
            "Eddy,Merckx,Men (P/1/2/3),15\r\n"
            "Greg,LeMond,Men (P/1/2/3),12\r\n"
        )
        f = tmp_path / "series.csv"
        f.write_text(csv_content, encoding="utf-8")

        entries = svc.import_series(f)
        assert len(entries) == 2
        assert entries[0].first_name == "Eddy"
        assert entries[0].last_name == "Merckx"
        assert entries[0].total_points == 15

    def test_3_column_format(self, svc, tmp_path):
        """Hand-edited format: CATEGORY, NAME, POINTS."""
        csv_content = (
            "Category,Name,Series Points\r\n"
            "Handcycle,Joe Pomeroy,4\r\n"
            ",,\r\n"
            "Master 50+ -Men,David Hoenicke,7\r\n"
        )
        f = tmp_path / "series.csv"
        f.write_text(csv_content, encoding="utf-8")

        entries = svc.import_series(f)
        assert len(entries) == 2
        assert entries[0].first_name == "Joe"
        assert entries[0].last_name == "Pomeroy"
        assert entries[0].category == "Handcycle"
        assert entries[0].total_points == 4
        assert entries[1].category == "Master 50+ -Men"

    def test_blank_rows_skipped(self, svc, tmp_path):
        csv_content = (
            "Category,Name,Points\r\n"
            "Cat A,Alice Smith,5\r\n"
            ",,\r\n"
            ",,\r\n"
            "Cat B,Bob Jones,3\r\n"
        )
        f = tmp_path / "series.csv"
        f.write_text(csv_content, encoding="utf-8")

        entries = svc.import_series(f)
        assert len(entries) == 2

    @pytest.mark.skipif(
        not (DISTRO / "2022.august.18" / "2022 TT series points.csv").exists(),
        reason="distro data not present",
    )
    def test_historical_2022_series(self, svc):
        entries = svc.import_series(DISTRO / "2022.august.18" / "2022 TT series points.csv")
        assert len(entries) > 10
        # Should have multiple categories
        categories = {e.category for e in entries}
        assert len(categories) > 3


class TestExportSeries:
    def test_round_trip(self, svc, tmp_path):
        entries = [
            SeriesEntry("Eddy", "Merckx", "Men (P/1/2/3)", 15),
            SeriesEntry("Greg", "LeMond", "Men (P/1/2/3)", 12),
        ]
        f = tmp_path / "series.csv"
        svc.export_series(f, entries)

        reimported = svc.import_series(f)
        assert len(reimported) == 2
        assert reimported[0].first_name == "Eddy"
        assert reimported[0].total_points == 15


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------

class TestExportHtml:
    def test_writes_html(self, svc, tmp_path):
        html = "<html><body><h1>Results</h1></body></html>"
        f = tmp_path / "results.html"
        svc.export_html(f, html)
        assert f.read_text() == html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestFormatPosition:
    def test_whole_number(self):
        assert _format_position(1.0) == "1"
        assert _format_position(10.0) == "10"

    def test_half(self):
        assert _format_position(0.5) == "0.5"
        assert _format_position(1.5) == "1.5"


# ---------------------------------------------------------------------------
# Historical round-trip: import from distro, export, re-import, compare
# ---------------------------------------------------------------------------

class TestHistoricalRoundTrips:
    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_start_list_round_trip_2022(self, svc, tmp_path):
        original = svc.import_start_list(DISTRO / "2022.july.28" / "tt-start-list.csv")

        out = tmp_path / "start.csv"
        svc.export_start_list(out, original.riders, original.finish_times, original.results)

        reimported = svc.import_start_list(out)
        assert len(reimported.riders) == len(original.riders)

        for orig, reimp in zip(original.riders, reimported.riders):
            assert orig.bib_number == reimp.bib_number
            assert orig.last_name == reimp.last_name
            assert orig.start_position == reimp.start_position

    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_finish_list_round_trip_2022(self, svc, tmp_path):
        original = svc.import_finish_list(DISTRO / "2022.july.28" / "tt-finish-list.csv")

        out = tmp_path / "finish.csv"
        svc.export_finish_list(out, original.rows)

        reimported = svc.import_finish_list(out)
        assert len(reimported.rows) == len(original.rows)

        for orig_row, reimp_row in zip(original.rows, reimported.rows):
            assert orig_row[0] == reimp_row[0]  # bib
            assert orig_row[4] == reimp_row[4]  # finish time
