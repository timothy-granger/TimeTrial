"""Results display — HTML browser with export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextBrowser, QFileDialog, QMessageBox,
)

from timetrial.config.settings import AppConfig
from timetrial.services.event_bus import EventBus
from timetrial.services.import_export_service import ImportExportService


class ResultsWidget(QWidget):
    """QTextBrowser showing race results HTML, with export button."""

    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._bus = event_bus
        self._current_html = ""

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        self._btn_export = QPushButton("Export Results")
        toolbar.addWidget(self._btn_export)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # HTML browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        layout.addWidget(self._browser)

    def _connect_signals(self) -> None:
        self._btn_export.clicked.connect(self._on_export)
        self._bus.results_updated.connect(self._on_results_updated)

    def _on_results_updated(self, html: str) -> None:
        self._current_html = html
        self._browser.setHtml(html)

    def _on_export(self) -> None:
        if not self._current_html:
            QMessageBox.information(self, "Export", "No results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results",
            self._config.default_results,
            "HTML (*.html)",
        )
        if not path:
            return

        try:
            svc = ImportExportService(self._config)
            svc.export_html(Path(path), self._current_html)
        except OSError as e:
            QMessageBox.warning(self, "Export Error", str(e))
