"""Starter display — secondary-monitor window with large countdown and rider info."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QFont, QPaintEvent, QPixmap
from PySide6.QtWidgets import QWidget

from timetrial.config.settings import AppConfig
from timetrial.services.event_bus import EventBus


class StarterDisplay(QWidget):
    """Frameless fullscreen window for the race starter.

    Displays:
    - Race title / sponsor text (top center, above rider name)
    - Logo image (top-right corner)
    - Current rider name (large font)
    - Countdown seconds (center, very large font)
    - Race clock (bottom-left)
    - Rider bib number (bottom-right)

    All data arrives via EventBus signals — no direct coupling to MainWindow.
    """

    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._bus = event_bus

        # Display state
        self._rider_name: str = ""
        self._rider_bib: str = ""
        self._countdown: str = ""
        self._next_rider: str = ""
        self._race_start: datetime | None = None
        self._elapsed_ms: int = 0

        # Load logo images if configured
        self._logo: QPixmap | None = None
        if config.logo_image:
            logo_path = Path(config.logo_image)
            if logo_path.exists():
                self._logo = QPixmap(str(logo_path))

        self._logo_left: QPixmap | None = None
        if config.logo_image_left:
            logo_left_path = Path(config.logo_image_left)
            if logo_left_path.exists():
                self._logo_left = QPixmap(str(logo_left_path))

        self.setWindowTitle("Starter Display")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: black;")

        self._connect_signals()

    def _connect_signals(self) -> None:
        self._bus.rider_on_ramp.connect(self._on_rider_on_ramp)
        self._bus.rider_on_deck.connect(self._on_rider_on_deck)
        self._bus.countdown_updated.connect(self._on_countdown)
        self._bus.elapsed_updated.connect(self._on_elapsed)
        self._bus.race_started.connect(self._on_race_started)
        self._bus.all_riders_started.connect(self._on_all_started)

    # -- Slots --

    def _on_rider_on_ramp(self, name: str, bib: str) -> None:
        self._rider_name = name
        self._rider_bib = f"# {bib}" if bib else ""
        self.update()

    def _on_rider_on_deck(self, name: str) -> None:
        self._next_rider = name
        self.update()

    def _on_countdown(self, seconds: float) -> None:
        if seconds >= 0:
            self._countdown = str(int(seconds))
        else:
            self._countdown = ""
        self.update()

    def _on_elapsed(self, elapsed_ms: int) -> None:
        self._elapsed_ms = elapsed_ms
        # Derive race_start from elapsed if not yet set
        # (handles case where display opened after race started)
        if self._race_start is None and elapsed_ms > 0:
            self._race_start = datetime.now() - timedelta(milliseconds=elapsed_ms)
        self.update()

    def _on_race_started(self) -> None:
        self._race_start = datetime.now()

    def _on_all_started(self) -> None:
        self._rider_name = ""
        self._rider_bib = ""
        self._countdown = ""
        self._next_rider = ""
        self.update()

    # -- Rendering --

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.white)

        w = self.width()
        h = self.height()

        # Fonts — scale relative to window height (config sizes tuned for 1080p)
        scale = h / 1080.0
        title_font = QFont("Times", max(12, int(self._config.starter_font_title * scale)), QFont.Weight.Bold)
        rider_font = QFont("Times", max(16, int(self._config.starter_font_rider * scale)), QFont.Weight.Bold)
        countdown_font = QFont("Times", max(40, int(self._config.starter_font_countdown * scale)), QFont.Weight.Bold)
        clock_font = QFont("Times", max(16, int(self._config.starter_font_clock * scale)), QFont.Weight.Bold)

        # Track vertical position
        y_cursor = 0

        # --- Logos (scaled to same height) ---
        max_logo_h = int(h * 0.15)

        if self._logo_left and not self._logo_left.isNull():
            scaled = self._logo_left.scaledToHeight(max_logo_h, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(15, 10, scaled)

        if self._logo and not self._logo.isNull():
            scaled = self._logo.scaledToHeight(max_logo_h, Qt.TransformationMode.SmoothTransformation)
            logo_x = w - scaled.width() - 15
            painter.drawPixmap(logo_x, 10, scaled)

        # --- Race title (top center, line 1) ---
        if self._config.race_title:
            painter.setFont(title_font)
            fm_title = painter.fontMetrics()
            text_w = fm_title.horizontalAdvance(self._config.race_title)
            cx = (w - text_w) // 2
            y_cursor = int(fm_title.height() * 1.1)
            painter.drawText(cx, y_cursor, self._config.race_title)

            # --- Race subtitle (top center, line 2, 3/4 size) ---
            if self._config.race_subtitle:
                subtitle_font = QFont("Times", max(10, int(self._config.starter_font_title * 0.75 * scale)), QFont.Weight.Bold)
                painter.setFont(subtitle_font)
                fm_sub = painter.fontMetrics()
                text_w = fm_sub.horizontalAdvance(self._config.race_subtitle)
                cx = (w - text_w) // 2
                y_cursor += int(fm_sub.height() * 1.3)
                painter.drawText(cx, y_cursor, self._config.race_subtitle)

            y_cursor += int(fm_title.height() * 0.3)  # spacing after title

        # --- Rider name + Countdown (vertically centered in remaining space) ---
        header_bottom = y_cursor
        footer_top = h - int(80 * scale)  # leave room for clock/bib at bottom

        painter.setFont(rider_font)
        fm_rider = painter.fontMetrics()
        painter.setFont(countdown_font)
        fm_countdown = painter.fontMetrics()

        # Total height of rider name + countdown block
        rider_h = fm_rider.height()
        countdown_h = fm_countdown.ascent()
        block_h = rider_h + countdown_h
        block_top = header_bottom + (footer_top - header_bottom - block_h) // 2

        # Draw rider name
        painter.setFont(rider_font)
        y_cursor = block_top + fm_rider.ascent()
        if self._rider_name:
            text_w = fm_rider.horizontalAdvance(self._rider_name)
            cx = (w - text_w) // 2
            painter.drawText(cx, y_cursor, self._rider_name)

        # Draw countdown
        painter.setFont(countdown_font)
        y_cursor += fm_countdown.ascent()
        if self._countdown:
            text_w = fm_countdown.horizontalAdvance(self._countdown)
            cx = (w - text_w) // 2
            painter.drawText(cx, y_cursor, self._countdown)

        # --- Race clock (bottom-left) ---
        painter.setFont(clock_font)
        fm_clock = painter.fontMetrics()

        race_time_str = self._format_race_clock()
        cx = 10
        cy = h - 25
        painter.drawText(cx, cy, race_time_str)

        # --- Bib number (bottom-right) ---
        if self._rider_bib:
            bib_w = fm_clock.horizontalAdvance(self._rider_bib)
            cx = w - bib_w - 10
            painter.drawText(cx, cy, self._rider_bib)

        painter.end()

    def _format_race_clock(self) -> str:
        """Format the race clock as the legacy app does: time of day."""
        if self._race_start is None:
            return ""

        # Current time = race start + elapsed
        current = self._race_start + timedelta(milliseconds=self._elapsed_ms)
        # Format as h:mm:ss AM/PM (cross-platform)
        hour_12 = current.hour % 12 or 12
        am_pm = "AM" if current.hour < 12 else "PM"
        return f"{hour_12}:{current.minute:02d}:{current.second:02d} {am_pm}"
