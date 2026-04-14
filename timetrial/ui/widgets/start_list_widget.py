"""Start list table with rider management toolbar."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QHeaderView, QFileDialog, QMessageBox, QAbstractItemView,
)

from timetrial.config.settings import AppConfig
from timetrial.models.rider import Rider
from timetrial.models.race import Race
from timetrial.models.result import NO_RESULT_SENTINEL


# ---------------------------------------------------------------------------
# Table Model
# ---------------------------------------------------------------------------

class RiderTableModel(QAbstractTableModel):
    """Model backed by the Race's rider list. Single source of truth."""

    COLUMNS = ["Bib #", "Last Name", "First Name", "Category", "Position", "Finish", "Result"]

    def __init__(self, race: Race, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._race = race
        # Finish/result strings keyed by bib (populated from import or live race)
        self._finish_times: dict[str, str] = {}
        self._results: dict[str, str] = {}

    # -- Properties for external access --

    @property
    def finish_times(self) -> dict[str, str]:
        return self._finish_times

    @property
    def results(self) -> dict[str, str]:
        return self._results

    # -- Qt Model Interface --

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._race.riders)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        rider = self._race.riders[index.row()]
        col = index.column()

        if col == 0:
            return rider.bib_number
        elif col == 1:
            return rider.last_name
        elif col == 2:
            return rider.first_name
        elif col == 3:
            return rider.category
        elif col == 4:
            return self._format_position(rider.start_position)
        elif col == 5:
            return self._finish_times.get(rider.bib_number, NO_RESULT_SENTINEL)
        elif col == 6:
            return self._results.get(rider.bib_number, NO_RESULT_SENTINEL)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # -- Mutation Methods --

    def add_rider(self, rider: Rider) -> int:
        """Insert a rider in sorted order. Returns the row index."""
        # Find insertion point
        row = 0
        for i, existing in enumerate(self._race.riders):
            if rider.start_position < existing.start_position:
                row = i
                break
        else:
            row = len(self._race.riders)

        self.beginInsertRows(QModelIndex(), row, row)
        self._race.riders.insert(row, rider)
        self.endInsertRows()
        return row

    def update_rider(self, row: int, rider: Rider) -> int:
        """Replace rider at row. If position changed, re-sort.

        Returns the new row index.
        """
        old_rider = self._race.riders[row]

        if old_rider.start_position == rider.start_position:
            # Position unchanged — update in place
            self._race.riders[row] = rider
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1),
            )
            return row
        else:
            # Position changed — remove and re-insert
            self.beginRemoveRows(QModelIndex(), row, row)
            self._race.riders.pop(row)
            self.endRemoveRows()
            return self.add_rider(rider)

    def remove_rider(self, row: int) -> None:
        """Mark rider as deleted (replace with placeholder) if no result,
        or just mark bib as ---- if they have a result."""
        rider = self._race.riders[row]
        finish = self._finish_times.get(rider.bib_number, NO_RESULT_SENTINEL)
        result = self._results.get(rider.bib_number, NO_RESULT_SENTINEL)

        if finish == NO_RESULT_SENTINEL and result == NO_RESULT_SENTINEL:
            # No result — mark as placeholder
            placeholder = Rider("----", "----", "----", "----", rider.start_position)
            self._race.riders[row] = placeholder
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1),
            )
        else:
            # Has result — just blank the identity but keep the slot
            placeholder = Rider("----", "----", "----", "----", rider.start_position)
            self._race.riders[row] = placeholder
            # Preserve the finish/result under original bib
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1),
            )

    def set_finish(self, bib: str, finish_time: str, result: str) -> None:
        """Update finish time and result for a bib number."""
        self._finish_times[bib] = finish_time
        self._results[bib] = result

        # Find the row and notify
        for row, rider in enumerate(self._race.riders):
            if rider.bib_number == bib:
                self.dataChanged.emit(
                    self.index(row, 5),
                    self.index(row, 6),
                )
                break

    def load_from_import(self, riders: list[Rider], finish_times: dict[str, str], results: dict[str, str]) -> None:
        """Bulk load from CSV import."""
        self.beginResetModel()
        self._race.riders = riders
        self._finish_times = dict(finish_times)
        self._results = dict(results)
        self.endResetModel()

    def clear(self) -> None:
        """Remove all riders."""
        self.beginResetModel()
        self._race.riders.clear()
        self._finish_times.clear()
        self._results.clear()
        self.endResetModel()

    # -- Helpers --

    @staticmethod
    def _format_position(position: float) -> str:
        if position == int(position):
            return str(int(position))
        return str(position)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class StartListWidget(QWidget):
    """Start list table with add/edit/remove/import/export toolbar."""

    # Emitted when results may have changed (after import with existing results)
    results_may_have_changed = Signal()

    def __init__(
        self,
        race: Race,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._race = race
        self._config = config

        self._model = RiderTableModel(race, self)

        self._init_ui()
        self._connect_signals()

    @property
    def model(self) -> RiderTableModel:
        return self._model

    # -- UI Setup --

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self._btn_add = QPushButton("Add Rider")
        self._btn_edit = QPushButton("Edit Rider")
        self._btn_remove = QPushButton("Remove Rider")
        self._btn_import = QPushButton("Import")
        self._btn_export = QPushButton("Export")

        self._btn_edit.setEnabled(False)
        self._btn_remove.setEnabled(False)

        for btn in (self._btn_add, self._btn_edit, self._btn_remove,
                    self._btn_import, self._btn_export):
            toolbar.addWidget(btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Table
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(False)  # We maintain our own sort

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

    def _connect_signals(self) -> None:
        self._btn_add.clicked.connect(self._on_add_rider)
        self._btn_edit.clicked.connect(self._on_edit_rider)
        self._btn_remove.clicked.connect(self._on_remove_rider)
        self._btn_import.clicked.connect(self._on_import)
        self._btn_export.clicked.connect(self._on_export)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    # -- Slot handlers --

    def _on_selection_changed(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        count = len(rows)
        self._btn_edit.setEnabled(count == 1)
        self._btn_remove.setEnabled(count >= 1)

    def _on_add_rider(self) -> None:
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog

        next_pos = self._race.next_start_position(self._config.start_interval_minutes)
        dlg = AddRiderDialog(
            categories=list(self._config.categories),
            race=self._race,
            default_position=next_pos,
            parent=self,
        )

        if dlg.exec():
            rider = dlg.get_rider()
            row = self._model.add_rider(rider)
            self._table.selectRow(row)

    def _on_edit_rider(self) -> None:
        from timetrial.ui.dialogs.add_rider_dialog import AddRiderDialog

        rows = self._table.selectionModel().selectedRows()
        if len(rows) != 1:
            return

        row = rows[0].row()
        rider = self._race.riders[row]

        dlg = AddRiderDialog(
            categories=list(self._config.categories),
            race=self._race,
            rider=rider,
            parent=self,
        )

        if dlg.exec():
            updated = dlg.get_rider()
            new_row = self._model.update_rider(row, updated)
            self._table.selectRow(new_row)

    def _on_remove_rider(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return

        # Process in reverse order so indices remain valid
        for index in sorted(rows, key=lambda idx: idx.row(), reverse=True):
            self._model.remove_rider(index.row())

    def _on_import(self) -> None:
        from timetrial.services.import_export_service import ImportExportService

        path, _ = QFileDialog.getOpenFileName(
            self, "Open TT Start List",
            self._config.default_start_list,
            "TT Start List (*.csv)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            data = svc.import_start_list(Path(path))
            self._model.load_from_import(data.riders, data.finish_times, data.results)
            self.results_may_have_changed.emit()
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Import Error", str(e))

    def _on_export(self) -> None:
        from timetrial.services.import_export_service import ImportExportService

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Start List",
            self._config.default_start_list,
            "CSV (*.csv)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            svc.export_start_list(
                Path(path),
                self._race.riders,
                self._model.finish_times,
                self._model.results,
            )
        except OSError as e:
            QMessageBox.warning(self, "Export Error", str(e))

    def set_race_running(self, running: bool) -> None:
        """Disable add/edit/import when race is running."""
        self._btn_add.setEnabled(not running)
        self._btn_import.setEnabled(not running)
        # Edit disabled during race (per legacy behavior)
        if running:
            self._btn_edit.setEnabled(False)
