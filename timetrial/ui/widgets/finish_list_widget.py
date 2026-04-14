"""Finish list table — capture finishes, enter bibs, auto-calculate results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QHeaderView, QFileDialog, QMessageBox, QAbstractItemView,
    QStyledItemDelegate, QLineEdit,
)

from timetrial.config.settings import AppConfig
from timetrial.models.race import Race, FinishRecord
from timetrial.models.result import NO_RESULT_SENTINEL
from timetrial.services.event_bus import EventBus
from timetrial.services.results_service import ResultsService
from timetrial.services.import_export_service import ImportExportService


# ---------------------------------------------------------------------------
# Finish row data — lightweight struct for display
# ---------------------------------------------------------------------------

class _FinishRow:
    """One row in the finish table."""
    __slots__ = ("bib", "last", "first", "category", "finish_time", "result")

    def __init__(self, finish_time: str) -> None:
        self.bib: str = ""
        self.last: str = ""
        self.first: str = ""
        self.category: str = ""
        self.finish_time: str = finish_time
        self.result: str = ""


# ---------------------------------------------------------------------------
# Table Model
# ---------------------------------------------------------------------------

class FinishTableModel(QAbstractTableModel):
    """Model for the finish times table."""

    COLUMNS = ["Bib #", "Last Name", "First Name", "Category", "Finish Time", "Result"]

    # Emitted when a bib is entered/changed and result calculated
    result_calculated = Signal(str, str, str)  # bib, finish_time_str, result_str

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[_FinishRow] = []

    @property
    def rows(self) -> list[_FinishRow]:
        return self._rows

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        row = self._rows[index.row()]
        col = index.column()
        if col == 0:
            return row.bib
        elif col == 1:
            return row.last
        elif col == 2:
            return row.first
        elif col == 3:
            return row.category
        elif col == 4:
            return row.finish_time
        elif col == 5:
            return row.result
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        # Only bib column (0) is editable
        if index.column() == 0:
            self._rows[index.row()].bib = str(value).strip()
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:  # Bib is editable
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    # -- Mutation --

    def add_finish(self, finish_time_str: str) -> int:
        """Add a new finish row. Returns the row index."""
        row_idx = len(self._rows)
        self.beginInsertRows(QModelIndex(), row_idx, row_idx)
        self._rows.append(_FinishRow(finish_time_str))
        self.endInsertRows()
        return row_idx

    def update_row(self, row: int, bib: str, last: str, first: str,
                   category: str, result: str) -> None:
        """Fill in rider info and result for a row."""
        r = self._rows[row]
        r.bib = bib
        r.last = last
        r.first = first
        r.category = category
        r.result = result
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, self.columnCount() - 1),
        )

    def update_finish_time(self, row: int, finish_time_str: str) -> None:
        """Update the finish time for a row (manual correction)."""
        self._rows[row].finish_time = finish_time_str
        idx = self.index(row, 4)
        self.dataChanged.emit(idx, idx)

    def load_from_import(self, rows: list[tuple[str, str, str, str, str, str]]) -> None:
        """Bulk load from CSV import."""
        self.beginResetModel()
        self._rows.clear()
        for bib, last, first, category, finish, result in rows:
            r = _FinishRow(finish)
            r.bib = bib
            r.last = last
            r.first = first
            r.category = category
            r.result = result
            self._rows.append(r)
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def get_export_rows(self) -> list[tuple[str, str, str, str, str, str]]:
        """Return rows as tuples for export."""
        return [
            (r.bib, r.last, r.first, r.category, r.finish_time, r.result)
            for r in self._rows
        ]


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class FinishListWidget(QWidget):
    """Finish list table with record-finish button, bib entry, and result calculation."""

    # Emitted when any result changes (triggers results HTML update)
    results_changed = Signal()

    def __init__(
        self,
        race: Race,
        config: AppConfig,
        event_bus: EventBus,
        results_svc: ResultsService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._race = race
        self._config = config
        self._bus = event_bus
        self._results_svc = results_svc

        self._model = FinishTableModel(self)
        self._processing_bib = False  # re-entrancy guard

        self._init_ui()
        self._connect_signals()

    @property
    def model(self) -> FinishTableModel:
        return self._model

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self._btn_record = QPushButton("Record Finish (Ctrl+T)")
        self._btn_record.setEnabled(False)
        self._btn_import = QPushButton("Import")
        self._btn_export = QPushButton("Export")

        toolbar.addWidget(self._btn_record)
        toolbar.addWidget(self._btn_import)
        toolbar.addWidget(self._btn_export)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Table
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

    def _connect_signals(self) -> None:
        self._btn_record.clicked.connect(self.record_finish)
        self._btn_import.clicked.connect(self._on_import)
        self._btn_export.clicked.connect(self._on_export)

        # When bib is edited, look up rider and calculate result
        self._model.dataChanged.connect(self._on_data_changed)

        # Enable record button when race starts
        self._bus.race_started.connect(lambda: self._btn_record.setEnabled(True))
        self._bus.race_stopped.connect(lambda: self._btn_record.setEnabled(False))

        # Double-click on finish time column opens edit dialog
        self._table.doubleClicked.connect(self._on_double_click)

    # -- Record finish --

    def record_finish(self) -> None:
        """Capture current time as a finish. User then enters bib."""
        now = datetime.now()
        finish_str = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"

        row = self._model.add_finish(finish_str)

        # Select the bib cell so user can type immediately
        bib_index = self._model.index(row, 0)
        self._table.setCurrentIndex(bib_index)
        self._table.edit(bib_index)

    # -- Bib entry and result calculation --

    def _on_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex) -> None:
        """When bib column changes, look up rider and calculate result."""
        if top_left.column() != 0:
            return

        # Guard against re-entrancy: update_row emits dataChanged which would recurse
        if self._processing_bib:
            return
        self._processing_bib = True

        try:
            self._process_bib_entry(top_left.row())
        finally:
            self._processing_bib = False

    def _process_bib_entry(self, row: int) -> None:
        """Look up rider by bib and calculate result."""
        finish_row = self._model.rows[row]
        bib = finish_row.bib.strip()

        if not bib:
            return

        rider = self._race.rider_by_bib(bib)
        if rider is None or rider.is_placeholder or rider.category == "----":
            # Bib not found or placeholder — show "Not Found" and clear fields
            self._model.update_row(row, bib, "(not found)", "", "", "")
            self._correct_scoring()
            self.results_changed.emit()
            return

        # Found — populate name/category
        finish_time_str = finish_row.finish_time

        if self._race.start_time and finish_time_str and finish_time_str != NO_RESULT_SENTINEL:
            try:
                result = self._results_svc.calculate_result(
                    rider, finish_time_str, self._race.start_time,
                )
                self._model.update_row(
                    row, bib, rider.last_name, rider.first_name,
                    rider.category, result.result_time_str,
                )
                # Notify start list model
                self._model.result_calculated.emit(bib, finish_time_str, result.result_time_str)
                self.results_changed.emit()
                return
            except (ValueError, OverflowError):
                pass

        # Fallback: populate name but no result
        self._model.update_row(row, bib, rider.last_name, rider.first_name, rider.category, "")
        self.results_changed.emit()

    # -- Edit finish time --

    def _on_double_click(self, index: QModelIndex) -> None:
        """Double-click on finish time column opens edit dialog."""
        if index.column() != 4:
            return

        from timetrial.ui.dialogs.edit_time_dialog import EditTimeDialog

        row = index.row()
        current_time_str = self._model.rows[row].finish_time

        dlg = EditTimeDialog(current_time_str, self._race.start_time, self)
        if dlg.exec():
            new_time_str = dlg.get_time_str()
            self._model.update_finish_time(row, new_time_str)

            # Recalculate result if bib is set
            bib = self._model.rows[row].bib.strip()
            if bib:
                # Trigger recalc by emitting dataChanged on bib column
                bib_index = self._model.index(row, 0)
                self._model.dataChanged.emit(bib_index, bib_index)

    # -- Scoring correction (port of correctScoring) --

    def _correct_scoring(self) -> None:
        """Verify that bibs in the start list have matching finish entries.
        Clear finish/result in start list for any unmatched bibs."""
        finish_bibs = {r.bib.strip() for r in self._model.rows if r.bib.strip()}

        for rider in self._race.riders:
            if rider.is_placeholder or rider.category == "----":
                continue
            if rider.bib_number not in finish_bibs:
                # Signal to clear this rider's finish/result
                self._model.result_calculated.emit(
                    rider.bib_number, NO_RESULT_SENTINEL, NO_RESULT_SENTINEL
                )

    # -- Import / Export --

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open TT Finish List",
            self._config.default_finish_list,
            "TT Finish List (*.csv)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            data = svc.import_finish_list(Path(path))
            self._model.load_from_import(data.rows)
            self._correct_scoring()
            self.results_changed.emit()
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Import Error", str(e))

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Finish List",
            self._config.default_finish_list,
            "CSV (*.csv)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            svc.export_finish_list(Path(path), self._model.get_export_rows())
        except OSError as e:
            QMessageBox.warning(self, "Export Error", str(e))
