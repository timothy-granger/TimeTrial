"""Tests for ResultsService."""

from datetime import datetime
from pathlib import Path

import pytest

from timetrial.config.settings import AppConfig, load_config
from timetrial.models.rider import Rider
from timetrial.models.race import Race
from timetrial.models.result import RaceResult, NO_RESULT_SENTINEL
from timetrial.services.results_service import (
    ResultsService,
    _format_elapsed_ms,
    _parse_result_to_ms,
    _parse_time_str,
)
from timetrial.services.import_export_service import ImportExportService

DISTRO = Path(__file__).parent.parent / "distro"


@pytest.fixture
def config() -> AppConfig:
    return load_config(user_path=Path("/nonexistent"))


@pytest.fixture
def svc(config) -> ResultsService:
    return ResultsService(config)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestFormatElapsedMs:
    def test_zero(self):
        assert _format_elapsed_ms(0) == "00:00:00.000"

    def test_one_second(self):
        assert _format_elapsed_ms(1000) == "00:00:01.000"

    def test_typical_result(self):
        # 22 minutes, 13 seconds, 297 ms
        ms = (22 * 60 + 13) * 1000 + 297
        assert _format_elapsed_ms(ms) == "00:22:13.297"

    def test_over_one_hour(self):
        ms = (1 * 3600 + 5 * 60 + 30) * 1000 + 500
        assert _format_elapsed_ms(ms) == "01:05:30.500"

    def test_negative_clamps_to_zero(self):
        assert _format_elapsed_ms(-100) == "00:00:00.000"


class TestParseResultToMs:
    def test_typical(self):
        assert _parse_result_to_ms("00:22:13.297") == (22 * 60 + 13) * 1000 + 297

    def test_sentinel(self):
        assert _parse_result_to_ms(NO_RESULT_SENTINEL) == 0

    def test_short_ms(self):
        # Only 2 decimal places
        assert _parse_result_to_ms("00:22:13.29") == (22 * 60 + 13) * 1000 + 290


class TestParseTimeStr:
    def test_typical(self):
        dt = _parse_time_str("18:25:05.245")
        assert dt.hour == 18
        assert dt.minute == 25
        assert dt.second == 5
        assert dt.microsecond == 245000  # 245 ms = 245000 us


# ---------------------------------------------------------------------------
# Single result calculation
# ---------------------------------------------------------------------------

class TestCalculateResult:
    def test_basic_calculation(self, svc):
        """Rider at position 1.0 (60s offset), race start at 18:00:01.315."""
        rider = Rider("42", "Merckx", "Eddy", "Men (P/1/2/3)", 1.0)
        race_start = datetime(2024, 7, 20, 18, 0, 1, 315000)  # 18:00:01.315

        # Rider's start: 18:00:01.315 + 60,000ms = 18:01:01.315
        # Rider finishes at 18:23:01.315 → elapsed = 22:00.000
        result = svc.calculate_result(rider, "18:23:01.315", race_start)

        assert result.bib_number == "42"
        assert result.result_time_str == "00:22:00.000"
        assert result.result_ms == 22 * 60 * 1000

    def test_30_second_offset(self, svc):
        """Rider at position 0.5 (30s offset)."""
        rider = Rider("1", "Smith", "John", "Men (4/5/U)", 0.5)
        race_start = datetime(2024, 7, 20, 18, 0, 0, 0)

        # Rider's start: 18:00:00.000 + 30,000ms = 18:00:30.000
        # Rider finishes at 18:24:30.000 → elapsed = 24:00.000
        result = svc.calculate_result(rider, "18:24:30.000", race_start)

        assert result.result_time_str == "00:24:00.000"
        assert result.result_ms == 24 * 60 * 1000

    def test_with_millisecond_precision(self, svc):
        """Verify millisecond-level accuracy."""
        rider = Rider("7", "A", "B", "Cat", 3.5)
        race_start = datetime(2024, 7, 20, 18, 0, 1, 315000)

        # Rider's start: 18:00:01.315 + 210,000ms = 18:03:31.315
        # Rider finishes at 18:24:58.946
        result = svc.calculate_result(rider, "18:24:58.946", race_start)

        # Expected: 18:24:58.946 - 18:03:31.315 = 21:27.631
        assert result.result_time_str == "00:21:27.631"
        assert result.result_ms == (21 * 60 + 27) * 1000 + 631

    def test_result_has_rider_info(self, svc):
        rider = Rider("42", "Merckx", "Eddy", "Men (P/1/2/3)", 1.0)
        race_start = datetime(2024, 7, 20, 18, 0, 0, 0)
        result = svc.calculate_result(rider, "18:23:00.000", race_start)

        assert result.first_name == "Eddy"
        assert result.last_name == "Merckx"
        assert result.category == "Men (P/1/2/3)"
        assert result.display_name == "Eddy Merckx"
        assert result.has_result is True


# ---------------------------------------------------------------------------
# Batch computation
# ---------------------------------------------------------------------------

class TestComputeAllResults:
    def test_skips_no_result_riders(self, svc):
        race = Race()
        race.start_time = datetime(2024, 7, 20, 18, 0, 0, 0)
        race.riders = [
            Rider("1", "Smith", "John", "Cat A", 0.5),
            Rider("2", "Jones", "Jane", "Cat B", 1.0),
        ]
        finish_times = {"1": "18:24:30.000"}
        result_strings = {"1": "00:24:00.000"}

        results = svc.compute_all_results(race, finish_times, result_strings)
        assert len(results) == 1
        assert results[0].bib_number == "1"

    def test_skips_placeholders(self, svc):
        race = Race()
        race.start_time = datetime(2024, 7, 20, 18, 0, 0, 0)
        race.riders = [
            Rider("----", "----", "----", "----", 1.0),
        ]
        results = svc.compute_all_results(race, {}, {})
        assert len(results) == 0

    def test_uses_precomputed_result_when_no_start_time(self, svc):
        """When race.start_time is None, fall back to stored result strings."""
        race = Race()
        race.riders = [
            Rider("1", "Smith", "John", "Cat A", 0.5),
        ]
        finish_times = {"1": "18:24:30.000"}
        result_strings = {"1": "00:24:00.000"}

        results = svc.compute_all_results(race, finish_times, result_strings)
        assert len(results) == 1
        assert results[0].result_time_str == "00:24:00.000"
        assert results[0].result_ms == 24 * 60 * 1000


# ---------------------------------------------------------------------------
# Grouping and filtering
# ---------------------------------------------------------------------------

class TestCategoryResults:
    def test_groups_and_sorts(self, svc):
        results = [
            RaceResult("1", "A", "B", "Cat X", "18:24:00.000", "00:24:00.000", 24 * 60 * 1000),
            RaceResult("2", "C", "D", "Cat X", "18:22:00.000", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("3", "E", "F", "Cat Y", "18:25:00.000", "00:25:00.000", 25 * 60 * 1000),
        ]
        groups = svc.category_results(results)

        assert "Cat X" in groups
        assert "Cat Y" in groups
        assert len(groups["Cat X"]) == 2
        # Fastest first within category
        assert groups["Cat X"][0].bib_number == "2"
        assert groups["Cat X"][1].bib_number == "1"

    def test_excludes_no_result(self, svc):
        results = [
            RaceResult("1", "A", "B", "Cat", "x", NO_RESULT_SENTINEL, 0),
        ]
        groups = svc.category_results(results)
        assert len(groups) == 0


class TestOverallResults:
    def test_excludes_juniors(self, svc):
        results = [
            RaceResult("1", "A", "B", "Men (P/1/2/3)", "x", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("2", "C", "D", "10-14 (M)", "x", "00:20:00.000", 20 * 60 * 1000),
            RaceResult("3", "E", "F", "15-18 (M)", "x", "00:21:00.000", 21 * 60 * 1000),
            RaceResult("4", "G", "H", "10-14 (F)", "x", "00:19:00.000", 19 * 60 * 1000),
            RaceResult("5", "I", "J", "15-18 (F)", "x", "00:23:00.000", 23 * 60 * 1000),
            RaceResult("6", "K", "L", "Women (P/1/2/3)", "x", "00:25:00.000", 25 * 60 * 1000),
        ]
        overall = svc.overall_results(results)

        assert len(overall) == 2
        bibs = [r.bib_number for r in overall]
        assert "2" not in bibs  # 10-14 (M) excluded
        assert "3" not in bibs  # 15-18 (M) excluded
        assert "4" not in bibs  # 10-14 (F) excluded
        assert "5" not in bibs  # 15-18 (F) excluded

    def test_sorted_fastest_first(self, svc):
        results = [
            RaceResult("1", "A", "B", "Cat A", "x", "00:25:00.000", 25 * 60 * 1000),
            RaceResult("2", "C", "D", "Cat B", "x", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("3", "E", "F", "Cat C", "x", "00:28:00.000", 28 * 60 * 1000),
        ]
        overall = svc.overall_results(results)
        assert [r.bib_number for r in overall] == ["2", "1", "3"]


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

class TestGenerateResultsHtml:
    def test_has_category_and_overall_sections(self, svc):
        results = [
            RaceResult("1", "Eddy", "Merckx", "Men (P/1/2/3)", "18:22:00.000", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("2", "Greg", "LeMond", "Men (4/5/U)", "18:24:00.000", "00:24:00.000", 24 * 60 * 1000),
        ]
        html = svc.generate_results_html(results)

        assert "<h2>Category Results</h2>" in html
        assert "<h2>Overall Results</h2>" in html
        assert "Eddy Merckx" in html
        assert "Greg LeMond" in html

    def test_overall_is_numbered(self, svc):
        results = [
            RaceResult("1", "Eddy", "Merckx", "Men (P/1/2/3)", "x", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("2", "Greg", "LeMond", "Men (4/5/U)", "x", "00:24:00.000", 24 * 60 * 1000),
        ]
        html = svc.generate_results_html(results)

        assert "  1)" in html
        assert "  2)" in html

    def test_juniors_in_category_but_not_overall(self, svc):
        results = [
            RaceResult("1", "A", "Adult", "Men (P/1/2/3)", "x", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("2", "B", "Junior", "10-14 (M)", "x", "00:20:00.000", 20 * 60 * 1000),
        ]
        html = svc.generate_results_html(results)

        # Junior should appear in category section
        assert "B Junior" in html

        # But overall should only have 1 entry
        lines = html.split("\n")
        overall_section = False
        overall_lines = []
        for line in lines:
            if "Overall Results" in line:
                overall_section = True
                continue
            if overall_section and line.strip() and line.strip() not in ("<pre>", "</pre>", "</body></html>"):
                overall_lines.append(line)
        assert len(overall_lines) == 1
        assert "A Adult" in overall_lines[0]

    def test_category_groups_separated_by_blank_lines(self, svc):
        results = [
            RaceResult("1", "A", "B", "Cat A", "x", "00:22:00.000", 22 * 60 * 1000),
            RaceResult("2", "C", "D", "Cat B", "x", "00:24:00.000", 24 * 60 * 1000),
        ]
        html = svc.generate_results_html(results)

        # There should be a blank line between categories in the <pre> section
        assert "\n\n" in html


# ---------------------------------------------------------------------------
# Integration: validate against historical distro data
# ---------------------------------------------------------------------------

class TestHistoricalValidation:
    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_imported_results_match_stored_results(self, config):
        """Import start list with known results, verify compute_all_results
        produces matching result strings when using pre-computed path."""
        io_svc = ImportExportService(config)
        results_svc = ResultsService(config)

        # Import the results CSV (has finish times and results filled in)
        data = io_svc.import_start_list(DISTRO / "2022.july.28" / "tt-start-list.results.csv")

        race = Race()
        race.riders = data.riders
        # No start_time → will use pre-computed result strings
        race.start_time = None

        results = results_svc.compute_all_results(race, data.finish_times, data.results)

        # Every rider with a non-sentinel result should be in results
        # (excluding placeholders and ---- category entries)
        expected_count = sum(
            1 for bib, res in data.results.items()
            if res != NO_RESULT_SENTINEL and not any(
                r.bib_number == bib and (r.is_placeholder or r.category == "----")
                for r in data.riders
            )
        )
        assert len(results) == expected_count

        # Result strings should match what was in the CSV
        for result in results:
            assert result.result_time_str == data.results[result.bib_number]

    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_category_results_have_all_categories(self, config):
        """All non-empty categories from historical data appear in grouped results."""
        io_svc = ImportExportService(config)
        results_svc = ResultsService(config)

        data = io_svc.import_start_list(DISTRO / "2022.july.28" / "tt-start-list.results.csv")
        race = Race()
        race.riders = data.riders

        results = results_svc.compute_all_results(race, data.finish_times, data.results)
        groups = results_svc.category_results(results)

        # Every real category that has a result should have a group
        cats_with_results = {
            r.category for r in data.riders
            if not r.is_placeholder and r.category != "----"
            and data.results.get(r.bib_number, NO_RESULT_SENTINEL) != NO_RESULT_SENTINEL
        }
        for cat in cats_with_results:
            assert cat in groups, f"Missing category group: {cat}"

    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_overall_results_exclude_juniors(self, config):
        """Verify junior categories are excluded from overall even with real data."""
        io_svc = ImportExportService(config)
        results_svc = ResultsService(config)

        data = io_svc.import_start_list(DISTRO / "2022.july.28" / "tt-start-list.results.csv")
        race = Race()
        race.riders = data.riders

        results = results_svc.compute_all_results(race, data.finish_times, data.results)
        overall = results_svc.overall_results(results)

        junior_cats = set(config.junior_categories)
        for r in overall:
            assert r.category not in junior_cats
