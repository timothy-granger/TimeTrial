"""Main application window — tab container and top-level coordination."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMessageBox,
)

from timetrial.config.settings import AppConfig
from timetrial.models.race import Race, RaceState
from timetrial.models.result import NO_RESULT_SENTINEL
from timetrial.services.event_bus import EventBus
from timetrial.services.timing_service import TimingService
from timetrial.services.results_service import ResultsService
from timetrial.services.series_service import SeriesService
from timetrial.services.import_export_service import ImportExportService
from timetrial.services.persistence_service import PersistenceService
from timetrial.ui.widgets.start_list_widget import StartListWidget
from timetrial.ui.widgets.finish_list_widget import FinishListWidget
from timetrial.ui.widgets.race_control_widget import RaceControlWidget
from timetrial.ui.widgets.results_widget import ResultsWidget
from timetrial.ui.widgets.series_widget import SeriesWidget
from timetrial.ui.starter_display import StarterDisplay


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(
        self,
        race: Race,
        config: AppConfig,
        event_bus: EventBus,
        timing_svc: TimingService,
        results_svc: ResultsService,
        series_svc: SeriesService,
        io_svc: ImportExportService,
        persistence_svc: Optional[PersistenceService] = None,
    ) -> None:
        super().__init__()
        self._race = race
        self._config = config
        self._bus = event_bus
        self._timing_svc = timing_svc
        self._results_svc = results_svc
        self._series_svc = series_svc
        self._io_svc = io_svc
        self._persistence = persistence_svc

        self.setWindowTitle("TimeTrial Scoring")
        self.resize(1200, 700)

        self._starter_display: StarterDisplay | None = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Race control bar (always visible at top)
        self._race_control = RaceControlWidget(self._timing_svc, self._bus, self)
        main_layout.addWidget(self._race_control)

        # Tab widget
        self._tabs = QTabWidget()
        main_layout.addWidget(self._tabs)

        # Tab 1: Start List
        self._start_list = StartListWidget(self._race, self._config, self)
        self._tabs.addTab(self._start_list, "Start List")

        # Tab 2: Finish Times
        self._finish_list = FinishListWidget(
            self._race, self._config, self._bus, self._results_svc, self,
        )
        self._tabs.addTab(self._finish_list, "Finish Times")

        # Tab 3: Results
        self._results_widget = ResultsWidget(self._config, self._bus, self)
        self._tabs.addTab(self._results_widget, "Results")

        # Tab 4: Series
        self._series_widget = SeriesWidget(
            self._race, self._config, self._bus,
            self._results_svc, self._series_svc, self,
        )
        self._series_widget.set_start_list_model(self._start_list.model)
        self._tabs.addTab(self._series_widget, "Series")

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def _connect_signals(self) -> None:
        # Race state
        self._bus.race_started.connect(self._on_race_started)
        self._bus.race_stopped.connect(self._on_race_stopped)
        self._bus.elapsed_updated.connect(self._on_elapsed_updated)

        # When finish list calculates a result, update start list model
        self._finish_list.model.result_calculated.connect(self._on_result_calculated)

        # When results change, regenerate results HTML and auto-save
        self._finish_list.results_changed.connect(self._on_results_changed)
        self._start_list.results_may_have_changed.connect(self._on_results_changed)

    # -- Recovery --

    def load_recovered_data(self, snapshot: dict) -> None:
        """Restore UI state from a recovered race snapshot."""
        riders = snapshot["riders"]
        finish_records = snapshot["finish_records"]

        # Build finish/result dicts for the start list model
        finish_times: dict[str, str] = {}
        results: dict[str, str] = {}
        for bib, finish_str, result_str in finish_records:
            if bib:
                finish_times[bib] = finish_str
                results[bib] = result_str

        # Load into start list
        self._start_list.model.load_from_import(riders, finish_times, results)

        # Load into finish list
        finish_rows = [
            (bib, "", "", "", finish_str, result_str)
            for bib, finish_str, result_str in finish_records
        ]
        # Populate name/category from rider lookup
        populated_rows = []
        for bib, finish_str, result_str in finish_records:
            rider = self._race.rider_by_bib(bib)
            if rider and not rider.is_placeholder:
                populated_rows.append(
                    (bib, rider.last_name, rider.first_name, rider.category, finish_str, result_str)
                )
            else:
                populated_rows.append((bib, "", "", "", finish_str, result_str))

        self._finish_list.model.load_from_import(populated_rows)

        # Regenerate results
        self._on_results_changed()

        self._status.showMessage("Race recovered from auto-save")

    # -- Slots --

    def _on_race_started(self) -> None:
        self._start_list.set_race_running(True)
        self._status.showMessage("Race in progress")
        self._auto_save()

    def _on_race_stopped(self) -> None:
        self._start_list.set_race_running(False)
        self._status.showMessage("Race stopped")
        if self._persistence:
            self._persistence.mark_race_completed()

    def _on_elapsed_updated(self, elapsed_ms: int) -> None:
        h = elapsed_ms // 3_600_000
        m = (elapsed_ms % 3_600_000) // 60_000
        s = (elapsed_ms % 60_000) // 1000
        ms = elapsed_ms % 1000
        self._status.showMessage(f"Elapsed: {h:02d}:{m:02d}:{s:02d}.{ms:03d}")

    def _on_result_calculated(self, bib: str, finish_time: str, result: str) -> None:
        """Update the start list model when a finish result is calculated."""
        self._start_list.model.set_finish(bib, finish_time, result)
        self._auto_save()

    def _on_results_changed(self) -> None:
        """Regenerate results HTML when any result changes."""
        results = self._results_svc.compute_all_results(
            self._race,
            self._start_list.model.finish_times,
            self._start_list.model.results,
        )
        html = self._results_svc.generate_results_html(results)
        self._bus.results_updated.emit(html)

    # -- Auto-save --

    def _auto_save(self) -> None:
        """Persist the current race state to SQLite."""
        if not self._persistence:
            return

        # Collect finish rows as (bib, finish_time, result)
        finish_rows = [
            (r.bib, r.finish_time, r.result)
            for r in self._finish_list.model.rows
            if r.bib.strip()
        ]

        self._persistence.auto_save(self._race, finish_rows)

    # -- Starter display --

    def _show_starter_display(self) -> None:
        """Create (if needed) and show the starter display window."""
        if self._starter_display is None:
            self._starter_display = StarterDisplay(self._config, self._bus)
        self._starter_display.show()
        self._starter_display.raise_()
        self._starter_display.activateWindow()

    # -- Key events --

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._finish_list.record_finish()
        elif event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._show_starter_display()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        reply = QMessageBox.question(
            self, "Exit TT Scoring Application",
            "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._starter_display is not None:
                self._starter_display.close()
            event.accept()
        else:
            event.ignore()
