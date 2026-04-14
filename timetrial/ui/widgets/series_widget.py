"""Series standings display — HTML browser with import/export/calculate."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextBrowser, QFileDialog, QMessageBox,
)

from timetrial.config.settings import AppConfig
from timetrial.models.race import Race
from timetrial.models.series import SeriesEntry
from timetrial.services.event_bus import EventBus
from timetrial.services.results_service import ResultsService
from timetrial.services.series_service import SeriesService
from timetrial.services.import_export_service import ImportExportService


class SeriesWidget(QWidget):
    """Series standings browser with import, calculate, and export."""

    def __init__(
        self,
        race: Race,
        config: AppConfig,
        event_bus: EventBus,
        results_svc: ResultsService,
        series_svc: SeriesService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._race = race
        self._config = config
        self._bus = event_bus
        self._results_svc = results_svc
        self._series_svc = series_svc

        self._standings: list[SeriesEntry] = []
        self._current_html = ""

        # Reference to start list model — set after construction
        self._start_list_model = None

        self._init_ui()
        self._connect_signals()

    def set_start_list_model(self, model) -> None:
        """Set reference to start list model for accessing finish/result data."""
        self._start_list_model = model

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        self._btn_import = QPushButton("Import Series")
        self._btn_calculate = QPushButton("Calculate Points")
        self._btn_export = QPushButton("Export Series")

        toolbar.addWidget(self._btn_import)
        toolbar.addWidget(self._btn_calculate)
        toolbar.addWidget(self._btn_export)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # HTML browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        layout.addWidget(self._browser)

    def _connect_signals(self) -> None:
        self._btn_import.clicked.connect(self._on_import)
        self._btn_calculate.clicked.connect(self._on_calculate)
        self._btn_export.clicked.connect(self._on_export)

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open TT Series Results",
            "", "TT Series Results (*.csv)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            self._standings = svc.import_series(Path(path))
            self._refresh_html()
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Import Error", str(e))

    def _on_calculate(self) -> None:
        """Award points from today's race and update cumulative standings."""
        if self._start_list_model is None:
            return

        # Compute today's results
        results = self._results_svc.compute_all_results(
            self._race,
            self._start_list_model.finish_times,
            self._start_list_model.results,
        )

        if not results:
            QMessageBox.information(self, "Calculate", "No race results to score.")
            return

        cat_results = self._results_svc.category_results(results)
        self._standings = self._series_svc.update_standings(self._standings, cat_results)
        self._refresh_html()

    def _on_export(self) -> None:
        if not self._current_html:
            QMessageBox.information(self, "Export", "No series data to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Series Points",
            "tt-series-results.html",
            "HTML (*.html)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            svc.export_html(Path(path), self._current_html)
        except OSError as e:
            QMessageBox.warning(self, "Export Error", str(e))

    def _refresh_html(self) -> None:
        self._current_html = self._series_svc.generate_series_html(self._standings)
        self._browser.setHtml(self._current_html)
        self._bus.series_updated.emit(self._current_html)
