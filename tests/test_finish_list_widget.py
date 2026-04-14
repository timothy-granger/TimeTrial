"""Tests for FinishTableModel and EditTimeDialog."""

from datetime import datetime
from pathlib import Path

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from timetrial.models.rider import Rider
from timetrial.models.race import Race
from timetrial.ui.widgets.finish_list_widget import FinishTableModel, FinishListWidget
from timetrial.ui.dialogs.edit_time_dialog import EditTimeDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def model(qapp):
    return FinishTableModel()


# ---------------------------------------------------------------------------
# FinishTableModel
# ---------------------------------------------------------------------------

class TestFinishTableModel:
    def test_empty_model(self, model):
        assert model.rowCount() == 0
        assert model.columnCount() == 6

    def test_add_finish(self, model):
        row = model.add_finish("18:24:30.123")
        assert row == 0
        assert model.rowCount() == 1
        assert model.data(model.index(0, 4)) == "18:24:30.123"  # finish time
        assert model.data(model.index(0, 0)) == ""  # bib empty

    def test_bib_is_editable(self, model):
        model.add_finish("18:24:30.123")
        flags = model.flags(model.index(0, 0))
        assert flags & Qt.ItemFlag.ItemIsEditable

    def test_other_columns_not_editable(self, model):
        model.add_finish("18:24:30.123")
        for col in (1, 2, 3, 4, 5):
            flags = model.flags(model.index(0, col))
            assert not (flags & Qt.ItemFlag.ItemIsEditable)

    def test_set_data_bib(self, model):
        model.add_finish("18:24:30.123")
        ok = model.setData(model.index(0, 0), "42", Qt.ItemDataRole.EditRole)
        assert ok
        assert model.data(model.index(0, 0)) == "42"

    def test_update_row(self, model):
        model.add_finish("18:24:30.123")
        model.update_row(0, "42", "Merckx", "Eddy", "Cat A", "00:22:00.000")

        assert model.data(model.index(0, 0)) == "42"
        assert model.data(model.index(0, 1)) == "Merckx"
        assert model.data(model.index(0, 2)) == "Eddy"
        assert model.data(model.index(0, 3)) == "Cat A"
        assert model.data(model.index(0, 5)) == "00:22:00.000"

    def test_update_finish_time(self, model):
        model.add_finish("18:24:30.123")
        model.update_finish_time(0, "18:25:00.000")
        assert model.data(model.index(0, 4)) == "18:25:00.000"

    def test_load_from_import(self, model):
        rows = [
            ("1", "Smith", "John", "Cat A", "18:24:30.123", "00:22:00.000"),
            ("2", "Jones", "Jane", "Cat B", "18:25:00.456", "00:23:00.456"),
        ]
        model.load_from_import(rows)
        assert model.rowCount() == 2
        assert model.data(model.index(0, 0)) == "1"
        assert model.data(model.index(1, 5)) == "00:23:00.456"

    def test_get_export_rows(self, model):
        model.add_finish("18:24:30.123")
        model.update_row(0, "42", "M", "E", "Cat", "00:22:00.000")

        export = model.get_export_rows()
        assert len(export) == 1
        assert export[0] == ("42", "M", "E", "Cat", "18:24:30.123", "00:22:00.000")

    def test_clear(self, model):
        model.add_finish("18:24:30.123")
        model.clear()
        assert model.rowCount() == 0

    def test_multiple_finishes_ordered(self, model):
        model.add_finish("18:24:30.000")
        model.add_finish("18:24:31.000")
        model.add_finish("18:24:32.000")

        assert model.rowCount() == 3
        assert model.data(model.index(0, 4)) == "18:24:30.000"
        assert model.data(model.index(2, 4)) == "18:24:32.000"

    def test_headers(self, model):
        for i, name in enumerate(FinishTableModel.COLUMNS):
            assert model.headerData(i, Qt.Orientation.Horizontal) == name


# ---------------------------------------------------------------------------
# FinishListWidget — bib entry handling
# ---------------------------------------------------------------------------

class TestFinishBibEntry:
    def test_unknown_bib_shows_not_found(self, qapp):
        """Entering a bib not in the start list should show '(not found)'."""
        from timetrial.config.settings import load_config
        from timetrial.services.event_bus import EventBus
        from timetrial.services.results_service import ResultsService

        config = load_config(user_path=Path("/nonexistent"))
        race = Race()
        race.riders = [Rider("1", "Smith", "John", "Cat A", 0.5)]
        race.start_time = datetime(2024, 7, 20, 18, 0, 0)
        event_bus = EventBus()
        results_svc = ResultsService(config)

        widget = FinishListWidget(race, config, event_bus, results_svc)
        widget.model.add_finish("18:24:30.000")
        # Simulate entering unknown bib "999"
        widget.model.setData(widget.model.index(0, 0), "999")
        # _on_data_changed should fire via signal — process manually
        widget._process_bib_entry(0)

        assert widget.model.data(widget.model.index(0, 1)) == "(not found)"
        assert widget.model.data(widget.model.index(0, 5)) == ""

    def test_valid_bib_calculates_result(self, qapp):
        """Entering a valid bib should auto-populate name and result."""
        from timetrial.config.settings import load_config
        from timetrial.services.event_bus import EventBus
        from timetrial.services.results_service import ResultsService

        config = load_config(user_path=Path("/nonexistent"))
        race = Race()
        race.riders = [Rider("1", "Smith", "John", "Cat A", 0.5)]
        race.start_time = datetime(2024, 7, 20, 18, 0, 0)
        event_bus = EventBus()
        results_svc = ResultsService(config)

        widget = FinishListWidget(race, config, event_bus, results_svc)
        widget.model.add_finish("18:24:30.000")
        widget.model.setData(widget.model.index(0, 0), "1")
        widget._process_bib_entry(0)

        assert widget.model.data(widget.model.index(0, 1)) == "Smith"
        assert widget.model.data(widget.model.index(0, 2)) == "John"
        assert widget.model.data(widget.model.index(0, 3)) == "Cat A"
        # Should have a calculated result
        assert widget.model.data(widget.model.index(0, 5)) != ""

    def test_placeholder_bib_shows_not_found(self, qapp):
        """Entering a bib that matches a placeholder should show not found."""
        from timetrial.config.settings import load_config
        from timetrial.services.event_bus import EventBus
        from timetrial.services.results_service import ResultsService

        config = load_config(user_path=Path("/nonexistent"))
        race = Race()
        race.riders = [Rider("----", "----", "----", "----", 0.5)]
        race.start_time = datetime(2024, 7, 20, 18, 0, 0)
        event_bus = EventBus()
        results_svc = ResultsService(config)

        widget = FinishListWidget(race, config, event_bus, results_svc)
        widget.model.add_finish("18:24:30.000")
        widget.model.setData(widget.model.index(0, 0), "----")
        widget._process_bib_entry(0)

        assert widget.model.data(widget.model.index(0, 1)) == "(not found)"


# ---------------------------------------------------------------------------
# EditTimeDialog
# ---------------------------------------------------------------------------

class TestEditTimeDialog:
    def test_parse_and_get_time(self, qapp):
        dlg = EditTimeDialog("18:24:30.123", None)
        result = dlg.get_time_str()
        assert result == "18:24:30.123"

    def test_with_race_start(self, qapp):
        race_start = datetime(2024, 7, 20, 18, 0, 0)
        dlg = EditTimeDialog("18:24:30.123", race_start)
        result = dlg.get_time_str()
        assert result == "18:24:30.123"

    def test_invalid_time_defaults_to_zero(self, qapp):
        dlg = EditTimeDialog("invalid", None)
        result = dlg.get_time_str()
        assert result == "00:00:00.000"
