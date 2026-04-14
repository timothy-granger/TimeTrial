"""Tests for SeriesService."""

from pathlib import Path

import pytest

from timetrial.config.settings import AppConfig, load_config
from timetrial.models.result import RaceResult
from timetrial.models.series import SeriesEntry
from timetrial.services.series_service import SeriesService
from timetrial.services.results_service import ResultsService
from timetrial.services.import_export_service import ImportExportService

DISTRO = Path(__file__).parent.parent / "distro"


@pytest.fixture
def config() -> AppConfig:
    return load_config(user_path=Path("/nonexistent"))


@pytest.fixture
def svc(config) -> SeriesService:
    return SeriesService(config)


def _make_result(bib: str, first: str, last: str, category: str, ms: int) -> RaceResult:
    return RaceResult(bib, first, last, category, "x", f"00:{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.000", ms)


# ---------------------------------------------------------------------------
# Points award
# ---------------------------------------------------------------------------

class TestAwardPoints:
    def test_top_five_get_points(self, svc):
        cat_results = {
            "Cat A": [
                _make_result("1", "A", "A", "Cat A", 1000 * i)
                for i in range(1, 8)  # 7 finishers
            ]
        }
        awards = svc.award_points(cat_results)

        assert len(awards) == 7
        points = [pts for _, pts in awards]
        assert points == [5, 4, 3, 2, 1, 0, 0]

    def test_fewer_than_five_finishers(self, svc):
        cat_results = {
            "Cat A": [
                _make_result("1", "A", "A", "Cat A", 1000),
                _make_result("2", "B", "B", "Cat A", 2000),
            ]
        }
        awards = svc.award_points(cat_results)

        points = [pts for _, pts in awards]
        assert points == [5, 4]

    def test_single_finisher(self, svc):
        cat_results = {
            "Cat A": [_make_result("1", "A", "A", "Cat A", 1000)]
        }
        awards = svc.award_points(cat_results)
        assert awards[0][1] == 5

    def test_multiple_categories_independent(self, svc):
        cat_results = {
            "Cat A": [
                _make_result("1", "A", "A", "Cat A", 1000),
                _make_result("2", "B", "B", "Cat A", 2000),
            ],
            "Cat B": [
                _make_result("3", "C", "C", "Cat B", 1500),
            ],
        }
        awards = svc.award_points(cat_results)

        # Cat A: 5, 4.  Cat B: 5 (resets per category)
        points_by_bib = {r.bib_number: pts for r, pts in awards}
        assert points_by_bib["1"] == 5
        assert points_by_bib["2"] == 4
        assert points_by_bib["3"] == 5

    def test_custom_points_table(self, config):
        """Verify that non-default points tables work."""
        # Create config with custom points
        custom = AppConfig(
            series_points=(10, 8, 6, 4, 2),
            categories=config.categories,
            junior_categories=config.junior_categories,
        )
        svc = SeriesService(custom)

        cat_results = {
            "Cat A": [_make_result(str(i), "X", "Y", "Cat A", i * 1000) for i in range(1, 7)]
        }
        awards = svc.award_points(cat_results)
        points = [pts for _, pts in awards]
        assert points == [10, 8, 6, 4, 2, 0]


# ---------------------------------------------------------------------------
# Update standings
# ---------------------------------------------------------------------------

class TestUpdateStandings:
    def test_new_racers_added(self, svc):
        """First-time racers should be added to standings."""
        standings: list[SeriesEntry] = []
        cat_results = {
            "Cat A": [
                _make_result("1", "Eddy", "Merckx", "Cat A", 1000),
                _make_result("2", "Greg", "LeMond", "Cat A", 2000),
            ]
        }
        updated = svc.update_standings(standings, cat_results)

        assert len(updated) == 2
        assert updated[0].first_name == "Eddy"
        assert updated[0].total_points == 5
        assert updated[1].first_name == "Greg"
        assert updated[1].total_points == 4

    def test_existing_racers_points_added(self, svc):
        """Existing racers should get points added to their total."""
        standings = [
            SeriesEntry("Eddy", "Merckx", "Cat A", 10),
        ]
        cat_results = {
            "Cat A": [_make_result("1", "Eddy", "Merckx", "Cat A", 1000)]
        }
        updated = svc.update_standings(standings, cat_results)

        assert len(updated) == 1
        assert updated[0].total_points == 15  # 10 + 5

    def test_mix_existing_and_new(self, svc):
        """Should update existing and add new in the same call."""
        standings = [
            SeriesEntry("Eddy", "Merckx", "Cat A", 10),
        ]
        cat_results = {
            "Cat A": [
                _make_result("1", "Eddy", "Merckx", "Cat A", 1000),
                _make_result("2", "Greg", "LeMond", "Cat A", 2000),
            ]
        }
        updated = svc.update_standings(standings, cat_results)

        assert len(updated) == 2
        eddy = next(e for e in updated if e.first_name == "Eddy")
        greg = next(e for e in updated if e.first_name == "Greg")
        assert eddy.total_points == 15  # 10 + 5
        assert greg.total_points == 4   # new, 2nd place

    def test_does_not_mutate_input(self, svc):
        """Original standings list should not be modified."""
        original = [SeriesEntry("Eddy", "Merckx", "Cat A", 10)]
        cat_results = {
            "Cat A": [_make_result("1", "Eddy", "Merckx", "Cat A", 1000)]
        }
        svc.update_standings(original, cat_results)
        assert original[0].total_points == 10  # unchanged

    def test_zero_points_not_added(self, svc):
        """Finishers with 0 points (6th place+) should not be added as new entries."""
        standings: list[SeriesEntry] = []
        cat_results = {
            "Cat A": [_make_result(str(i), f"R{i}", "X", "Cat A", i * 1000) for i in range(1, 8)]
        }
        updated = svc.update_standings(standings, cat_results)

        # Only 5 entries (those who received points), not 7
        assert len(updated) == 5

    def test_category_must_match(self, svc):
        """Same name in different category should create separate entry."""
        standings = [
            SeriesEntry("Eddy", "Merckx", "Cat A", 10),
        ]
        cat_results = {
            "Cat B": [_make_result("1", "Eddy", "Merckx", "Cat B", 1000)]
        }
        updated = svc.update_standings(standings, cat_results)

        assert len(updated) == 2  # Two separate entries
        cat_a = next(e for e in updated if e.category == "Cat A")
        cat_b = next(e for e in updated if e.category == "Cat B")
        assert cat_a.total_points == 10
        assert cat_b.total_points == 5


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

class TestGenerateSeriesHtml:
    def test_basic_structure(self, svc):
        standings = [
            SeriesEntry("Eddy", "Merckx", "Cat A", 15),
            SeriesEntry("Greg", "LeMond", "Cat A", 10),
            SeriesEntry("Fausto", "Coppi", "Cat B", 8),
        ]
        html = svc.generate_series_html(standings)

        assert "<html><body>" in html
        assert "</body></html>" in html
        assert "<h2>Cat A</h2>" in html
        assert "<h2>Cat B</h2>" in html
        assert "Eddy Merckx" in html
        assert "Greg LeMond" in html
        assert "Fausto Coppi" in html

    def test_sorted_by_points_descending(self, svc):
        standings = [
            SeriesEntry("Greg", "LeMond", "Cat A", 10),
            SeriesEntry("Eddy", "Merckx", "Cat A", 15),
        ]
        html = svc.generate_series_html(standings)

        # Eddy (15) should appear before Greg (10)
        eddy_pos = html.index("Eddy Merckx")
        greg_pos = html.index("Greg LeMond")
        assert eddy_pos < greg_pos

    def test_grouped_by_category(self, svc):
        standings = [
            SeriesEntry("A", "B", "Zulu", 5),
            SeriesEntry("C", "D", "Alpha", 10),
        ]
        html = svc.generate_series_html(standings)

        # Alpha should appear before Zulu (alphabetical)
        alpha_pos = html.index("Alpha")
        zulu_pos = html.index("Zulu")
        assert alpha_pos < zulu_pos

    def test_table_per_category(self, svc):
        standings = [
            SeriesEntry("A", "B", "Cat A", 5),
            SeriesEntry("C", "D", "Cat B", 10),
        ]
        html = svc.generate_series_html(standings)

        assert html.count("<table") == 2
        assert html.count("</table>") == 2

    def test_empty_standings(self, svc):
        html = svc.generate_series_html([])
        assert "<html><body>" in html
        assert "</body></html>" in html
        assert "<table" not in html

    def test_points_in_table_cells(self, svc):
        standings = [SeriesEntry("Eddy", "Merckx", "Cat A", 15)]
        html = svc.generate_series_html(standings)
        assert "<td>15</td>" in html


# ---------------------------------------------------------------------------
# Integration with historical data
# ---------------------------------------------------------------------------

class TestHistoricalIntegration:
    @pytest.mark.skipif(
        not (DISTRO / "2022.august.18" / "2022 TT series points.csv").exists(),
        reason="distro data not present",
    )
    def test_import_and_generate_html(self, config):
        """Import real series data, generate HTML, verify structure."""
        io_svc = ImportExportService(config)
        series_svc = SeriesService(config)

        entries = io_svc.import_series(DISTRO / "2022.august.18" / "2022 TT series points.csv")
        html = series_svc.generate_series_html(entries)

        assert "<html><body>" in html
        # Should have multiple category headers
        assert html.count("<h2>") >= 3
        # Spot-check a known entry from the file
        assert "Joe Pomeroy" in html

    @pytest.mark.skipif(not (DISTRO / "2022.july.28").exists(), reason="distro data not present")
    def test_award_and_update_from_race_results(self, config):
        """Full flow: import race results → award points → update empty standings."""
        io_svc = ImportExportService(config)
        results_svc = ResultsService(config)
        series_svc = SeriesService(config)

        # Load race results
        data = io_svc.import_start_list(DISTRO / "2022.july.28" / "tt-start-list.results.csv")
        race_results = results_svc.compute_all_results(
            race=type("R", (), {"riders": data.riders, "start_time": None})(),
            finish_times=data.finish_times,
            result_strings=data.results,
        )
        cat_results = results_svc.category_results(race_results)

        # Award points from empty standings
        standings = series_svc.update_standings([], cat_results)

        # Should have entries — one per finisher who earned points
        assert len(standings) > 0

        # Top finisher per category should have 5 points
        for category, results in cat_results.items():
            if results:
                top = results[0]
                entry = next(
                    (e for e in standings
                     if e.first_name == top.first_name and e.last_name == top.last_name
                     and e.category == top.category),
                    None,
                )
                assert entry is not None
                assert entry.total_points == 5
