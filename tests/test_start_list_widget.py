"""Tests for RiderTableModel and StartListWidget."""

from pathlib import Path

import pytest

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QApplication

from timetrial.config.settings import load_config
from timetrial.models.rider import Rider
from timetrial.models.race import Race
from timetrial.models.result import NO_RESULT_SENTINEL
from timetrial.ui.widgets.start_list_widget import RiderTableModel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def race():
    return Race()


@pytest.fixture
def model(race, qapp):
    return RiderTableModel(race)


# ---------------------------------------------------------------------------
# RiderTableModel
# ---------------------------------------------------------------------------

class TestRiderTableModel:
    def test_empty_model(self, model):
        assert model.rowCount() == 0
        assert model.columnCount() == 7

    def test_add_rider(self, model, race):
        rider = Rider("1", "Smith", "John", "Cat A", 0.5)
        row = model.add_rider(rider)
        assert row == 0
        assert model.rowCount() == 1

        # Check data via model API
        assert model.data(model.index(0, 0)) == "1"       # bib
        assert model.data(model.index(0, 1)) == "Smith"    # last
        assert model.data(model.index(0, 2)) == "John"     # first
        assert model.data(model.index(0, 3)) == "Cat A"    # category
        assert model.data(model.index(0, 4)) == "0.5"      # position
        assert model.data(model.index(0, 5)) == NO_RESULT_SENTINEL
        assert model.data(model.index(0, 6)) == NO_RESULT_SENTINEL

    def test_add_maintains_sort_order(self, model):
        model.add_rider(Rider("1", "A", "B", "Cat", 1.0))
        model.add_rider(Rider("3", "E", "F", "Cat", 3.0))
        model.add_rider(Rider("2", "C", "D", "Cat", 2.0))

        assert model.data(model.index(0, 0)) == "1"
        assert model.data(model.index(1, 0)) == "2"
        assert model.data(model.index(2, 0)) == "3"

    def test_update_rider_same_position(self, model, race):
        model.add_rider(Rider("1", "Smith", "John", "Cat A", 1.0))
        updated = Rider("1", "Jones", "Jane", "Cat B", 1.0)
        new_row = model.update_rider(0, updated)

        assert new_row == 0
        assert model.data(model.index(0, 1)) == "Jones"
        assert model.data(model.index(0, 3)) == "Cat B"

    def test_update_rider_changed_position(self, model):
        model.add_rider(Rider("1", "A", "B", "Cat", 1.0))
        model.add_rider(Rider("2", "C", "D", "Cat", 2.0))
        model.add_rider(Rider("3", "E", "F", "Cat", 3.0))

        # Move rider 1 from position 1.0 to 2.5
        updated = Rider("1", "A", "B", "Cat", 2.5)
        new_row = model.update_rider(0, updated)

        assert new_row == 1  # between rider 2 (pos 2.0) and rider 3 (pos 3.0)
        assert model.data(model.index(0, 0)) == "2"  # rider 2 now first
        assert model.data(model.index(1, 0)) == "1"  # rider 1 moved here
        assert model.data(model.index(2, 0)) == "3"

    def test_remove_rider_no_result(self, model):
        model.add_rider(Rider("1", "Smith", "John", "Cat A", 1.0))
        model.remove_rider(0)

        assert model.rowCount() == 1
        assert model.data(model.index(0, 0)) == "----"  # placeholder
        assert model.data(model.index(0, 1)) == "----"

    def test_set_finish(self, model):
        model.add_rider(Rider("1", "Smith", "John", "Cat A", 1.0))
        model.set_finish("1", "18:24:30.000", "00:24:00.000")

        assert model.data(model.index(0, 5)) == "18:24:30.000"
        assert model.data(model.index(0, 6)) == "00:24:00.000"

    def test_load_from_import(self, model):
        riders = [
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("2", "C", "D", "Cat", 1.0),
        ]
        finishes = {"1": "18:24:30.000"}
        results = {"1": "00:24:00.000"}

        model.load_from_import(riders, finishes, results)

        assert model.rowCount() == 2
        assert model.data(model.index(0, 5)) == "18:24:30.000"
        assert model.data(model.index(1, 5)) == NO_RESULT_SENTINEL

    def test_clear(self, model):
        model.add_rider(Rider("1", "A", "B", "Cat", 1.0))
        model.clear()
        assert model.rowCount() == 0

    def test_headers(self, model):
        for i, name in enumerate(RiderTableModel.COLUMNS):
            assert model.headerData(i, Qt.Orientation.Horizontal) == name

    def test_position_formatting(self, model):
        model.add_rider(Rider("1", "A", "B", "Cat", 1.0))
        model.add_rider(Rider("2", "C", "D", "Cat", 1.5))

        assert model.data(model.index(0, 4)) == "1"    # whole number
        assert model.data(model.index(1, 4)) == "1.5"   # half


# ---------------------------------------------------------------------------
# AddRiderDialog validation (programmatic, no interaction)
# ---------------------------------------------------------------------------

class TestAddRiderDialog:
    def test_create_and_get_rider(self, qapp):
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog

        race = Race()
        dlg = AddRiderDialog(
            categories=["Cat A", "Cat B"],
            race=race,
            default_position=1.0,
        )

        # Simulate filling fields
        dlg._bib.setText("42")
        dlg._last.setText("Merckx")
        dlg._first.setText("Eddy")
        dlg._category.setCurrentIndex(0)
        dlg._position.setValue(1.0)

        rider = dlg.get_rider()
        assert rider.bib_number == "42"
        assert rider.last_name == "Merckx"
        assert rider.first_name == "Eddy"
        assert rider.category == "Cat A"
        assert rider.start_position == 1.0

    def test_validation_empty_fields_disables_ok(self, qapp):
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog
        from PySide6.QtWidgets import QDialogButtonBox

        race = Race()
        dlg = AddRiderDialog(categories=["Cat A"], race=race, default_position=1.0)

        # All empty — OK should be disabled
        ok_btn = dlg._buttons.button(QDialogButtonBox.StandardButton.Ok)
        assert not ok_btn.isEnabled()

        # Fill bib only — still disabled
        dlg._bib.setText("1")
        assert not ok_btn.isEnabled()

        # Fill names — now enabled
        dlg._last.setText("Smith")
        dlg._first.setText("John")
        assert ok_btn.isEnabled()

    def test_validation_duplicate_bib(self, qapp):
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog
        from PySide6.QtWidgets import QDialogButtonBox

        race = Race()
        race.riders = [Rider("1", "A", "B", "Cat", 0.5)]

        dlg = AddRiderDialog(categories=["Cat A"], race=race, default_position=1.0)
        dlg._bib.setText("1")
        dlg._last.setText("Smith")
        dlg._first.setText("John")

        ok_btn = dlg._buttons.button(QDialogButtonBox.StandardButton.Ok)
        assert not ok_btn.isEnabled()
        assert "already in use" in dlg._status.text()

    def test_validation_duplicate_position(self, qapp):
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog
        from PySide6.QtWidgets import QDialogButtonBox

        race = Race()
        race.riders = [Rider("1", "A", "B", "Cat", 1.0)]

        dlg = AddRiderDialog(categories=["Cat A"], race=race, default_position=1.0)
        dlg._bib.setText("2")
        dlg._last.setText("Smith")
        dlg._first.setText("John")

        ok_btn = dlg._buttons.button(QDialogButtonBox.StandardButton.Ok)
        assert not ok_btn.isEnabled()
        assert "already taken" in dlg._status.text()

    def test_edit_mode_allows_same_bib(self, qapp):
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog
        from PySide6.QtWidgets import QDialogButtonBox

        existing = Rider("1", "Smith", "John", "Cat A", 1.0)
        race = Race()
        race.riders = [existing]

        dlg = AddRiderDialog(
            categories=["Cat A"], race=race,
            rider=existing,  # edit mode
        )

        ok_btn = dlg._buttons.button(QDialogButtonBox.StandardButton.Ok)
        assert ok_btn.isEnabled()  # Same bib is OK when editing
