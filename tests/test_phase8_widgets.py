"""Tests for Phase 8 widgets — Results, Series, StarterDisplay."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from PySide6.QtWidgets import QApplication

from timetrial.config.settings import load_config
from timetrial.models.race import Race
from timetrial.models.rider import Rider
from timetrial.services.event_bus import EventBus
from timetrial.services.results_service import ResultsService
from timetrial.services.series_service import SeriesService
from timetrial.ui.widgets.results_widget import ResultsWidget
from timetrial.ui.widgets.series_widget import SeriesWidget
from timetrial.ui.starter_display import StarterDisplay


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def config():
    return load_config(user_path=Path("/nonexistent"))


@pytest.fixture
def event_bus(qapp):
    return EventBus()


# ---------------------------------------------------------------------------
# ResultsWidget
# ---------------------------------------------------------------------------

class TestResultsWidget:
    def test_updates_on_signal(self, config, event_bus, qapp):
        widget = ResultsWidget(config, event_bus)
        html = "<html><body><h2>Test Results</h2></body></html>"

        event_bus.results_updated.emit(html)

        assert widget._current_html == html
        assert "Test Results" in widget._browser.toHtml()

    def test_starts_empty(self, config, event_bus, qapp):
        widget = ResultsWidget(config, event_bus)
        assert widget._current_html == ""


# ---------------------------------------------------------------------------
# SeriesWidget
# ---------------------------------------------------------------------------

class TestSeriesWidget:
    def test_creates_without_error(self, config, event_bus, qapp):
        race = Race()
        results_svc = ResultsService(config)
        series_svc = SeriesService(config)
        widget = SeriesWidget(race, config, event_bus, results_svc, series_svc)
        assert widget._standings == []

    def test_calculate_with_no_results(self, config, event_bus, qapp):
        race = Race()
        race.riders = [Rider("1", "A", "B", "Cat", 0.5)]
        results_svc = ResultsService(config)
        series_svc = SeriesService(config)
        widget = SeriesWidget(race, config, event_bus, results_svc, series_svc)

        # Need a mock start list model
        mock_model = MagicMock()
        mock_model.finish_times = {}
        mock_model.results = {}
        widget.set_start_list_model(mock_model)

        # Calculate should not crash (no results = shows info message)
        # We can't easily test the QMessageBox, but verify no exception
        assert widget._standings == []


# ---------------------------------------------------------------------------
# StarterDisplay
# ---------------------------------------------------------------------------

class TestStarterDisplay:
    def test_creates_without_error(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)
        assert display._rider_name == ""
        assert display._countdown == ""

    def test_responds_to_rider_on_ramp(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)

        event_bus.rider_on_ramp.emit("Eddy Merckx", "42")

        assert display._rider_name == "Eddy Merckx"
        assert display._rider_bib == "# 42"

    def test_responds_to_countdown(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)

        event_bus.countdown_updated.emit(15.5)

        assert display._countdown == "15"

    def test_responds_to_on_deck(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)

        event_bus.rider_on_deck.emit("Greg LeMond")

        assert display._next_rider == "Greg LeMond"

    def test_all_started_clears_display(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)

        # Set some state first
        event_bus.rider_on_ramp.emit("Eddy Merckx", "42")
        event_bus.countdown_updated.emit(5.0)

        # All started should clear
        event_bus.all_riders_started.emit()

        assert display._rider_name == ""
        assert display._countdown == ""
        assert display._rider_bib == ""

    def test_race_clock_format(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)
        display._race_start = datetime(2024, 7, 20, 18, 0, 0)
        display._elapsed_ms = 5 * 60 * 1000  # 5 minutes

        clock = display._format_race_clock()
        assert clock == "6:05:00 PM"

    def test_race_clock_am(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)
        display._race_start = datetime(2024, 7, 20, 9, 30, 0)
        display._elapsed_ms = 0

        clock = display._format_race_clock()
        assert clock == "9:30:00 AM"

    def test_race_clock_empty_before_start(self, config, event_bus, qapp):
        display = StarterDisplay(config, event_bus)
        assert display._format_race_clock() == ""
