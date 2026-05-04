"""Race control panel — start/stop, elapsed, countdown, rider status."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
    QPushButton, QLabel, QMessageBox,
)

from timetrial.services.event_bus import EventBus
from timetrial.services.timing_service import TimingService


class RaceControlWidget(QWidget):
    """Embeddable widget: start/stop timer, elapsed time, countdown,
    rider on-ramp / on-deck / in-hole display."""

    new_race_requested = Signal()
    clear_web_results_requested = Signal()

    def __init__(
        self,
        timing_svc: TimingService,
        event_bus: EventBus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._timing = timing_svc
        self._bus = event_bus
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- Left: Start/Stop buttons + elapsed ---
        control_box = QGroupBox("Race Control")
        ctrl_layout = QVBoxLayout(control_box)

        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("Start Race")
        self._btn_stop = QPushButton("Stop Race")
        self._btn_new = QPushButton("New Race")
        self._btn_stop.setEnabled(False)
        self._btn_clear_web = QPushButton("Clear Web Results")
        self._btn_clear_web.setEnabled(False)  # enabled when web publish service is available
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(self._btn_new)
        btn_row.addWidget(self._btn_clear_web)
        ctrl_layout.addLayout(btn_row)

        self._lbl_elapsed = QLabel("Elapsed: --:--:--.---")
        self._lbl_elapsed.setStyleSheet("font-size: 16px; font-weight: bold;")
        ctrl_layout.addWidget(self._lbl_elapsed)

        layout.addWidget(control_box)

        # --- Center: Countdown ---
        countdown_box = QGroupBox("Countdown")
        cd_layout = QVBoxLayout(countdown_box)
        self._lbl_countdown = QLabel("--")
        self._lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_countdown.setStyleSheet("font-size: 48px; font-weight: bold;")
        cd_layout.addWidget(self._lbl_countdown)
        layout.addWidget(countdown_box)

        # --- Right: Rider status ---
        rider_box = QGroupBox("Riders")
        rider_layout = QVBoxLayout(rider_box)

        self._lbl_on_ramp = QLabel("On the Ramp: —")
        self._lbl_on_ramp.setStyleSheet("font-size: 14px; font-weight: bold;")
        rider_layout.addWidget(self._lbl_on_ramp)

        self._lbl_on_deck = QLabel("On Deck: —")
        self._lbl_on_deck.setStyleSheet("font-size: 13px;")
        rider_layout.addWidget(self._lbl_on_deck)

        self._lbl_in_hole = QLabel("In the Hole: —")
        self._lbl_in_hole.setStyleSheet("font-size: 13px;")
        rider_layout.addWidget(self._lbl_in_hole)

        layout.addWidget(rider_box)

        # Stretch ratios
        layout.setStretch(0, 2)
        layout.setStretch(1, 1)
        layout.setStretch(2, 3)

    def _connect_signals(self) -> None:
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_new.clicked.connect(self._on_new_race)
        self._btn_clear_web.clicked.connect(self._on_clear_web_results)

        self._bus.elapsed_updated.connect(self._on_elapsed)
        self._bus.countdown_updated.connect(self._on_countdown)
        self._bus.rider_on_ramp.connect(self._on_rider_on_ramp)
        self._bus.rider_on_deck.connect(self._on_rider_on_deck)
        self._bus.rider_in_hole.connect(self._on_rider_in_hole)
        self._bus.all_riders_started.connect(self._on_all_started)
        self._bus.race_started.connect(self._on_race_started)
        self._bus.race_stopped.connect(self._on_race_stopped)

    # -- Button handlers --

    def _on_start(self) -> None:
        self._timing.start_race()

    def _on_stop(self) -> None:
        reply = QMessageBox.question(
            self, "Stop Race",
            "Are you sure you want to stop the race timer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._timing.stop_race()

    def _on_new_race(self) -> None:
        if self._timing.is_running:
            QMessageBox.warning(self, "New Race", "Stop the current race first.")
            return

        reply = QMessageBox.question(
            self, "New Race",
            "Start a new race?\n\nMake sure you've exported the current results first.\n"
            "This will clear all riders, finish times, and results.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.new_race_requested.emit()

    def _on_clear_web_results(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Web Results",
            "Clear the live results from the web?\n\n"
            "This will remove all results currently visible on GitHub Pages.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_web_results_requested.emit()

    def enable_clear_web_results(self, enabled: bool = True) -> None:
        """Enable the Clear Web Results button (called when web publish service is available)."""
        self._btn_clear_web.setEnabled(enabled)

    # -- EventBus slots --

    def _on_race_started(self) -> None:
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

    def _on_race_stopped(self) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def reset_display(self) -> None:
        """Reset all display elements for a new race."""
        self._lbl_elapsed.setText("Elapsed: --:--:--.---")
        self._lbl_countdown.setText("--")
        self._lbl_on_ramp.setText("On the Ramp: —")
        self._lbl_on_deck.setText("On Deck: —")
        self._lbl_in_hole.setText("In the Hole: —")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_elapsed(self, elapsed_ms: int) -> None:
        h = elapsed_ms // 3_600_000
        m = (elapsed_ms % 3_600_000) // 60_000
        s = (elapsed_ms % 60_000) // 1000
        ms = elapsed_ms % 1000
        self._lbl_elapsed.setText(f"Elapsed: {h:02d}:{m:02d}:{s:02d}.{ms:03d}")

    def _on_countdown(self, seconds: float) -> None:
        if seconds >= 0:
            self._lbl_countdown.setText(f"{int(seconds)}")
        else:
            self._lbl_countdown.setText("GO")

    def _on_rider_on_ramp(self, name: str, bib: str) -> None:
        if name:
            self._lbl_on_ramp.setText(f"On the Ramp: {name}  (#{bib})")
        else:
            self._lbl_on_ramp.setText("On the Ramp: —")

    def _on_rider_on_deck(self, name: str) -> None:
        self._lbl_on_deck.setText(f"On Deck: {name}" if name else "On Deck: —")

    def _on_rider_in_hole(self, name: str) -> None:
        self._lbl_in_hole.setText(f"In the Hole: {name}" if name else "In the Hole: —")

    def _on_all_started(self) -> None:
        self._lbl_countdown.setText("--")
        self._lbl_on_ramp.setText("On the Ramp: — (all started)")
        self._lbl_on_deck.setText("On Deck: —")
        self._lbl_in_hole.setText("In the Hole: —")
