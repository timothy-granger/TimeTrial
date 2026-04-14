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

        # Load logo image if configured
        self._logo: QPixmap | None = None
        if config.logo_image:
            logo_path = Path(config.logo_image)
            if logo_path.exists():
                self._logo = QPixmap(str(logo_path))

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

        # Fonts (sizes from config)
        title_font = QFont("Times", self._config.starter_font_title, QFont.Weight.Bold)
        rider_font = QFont("Times", self._config.starter_font_rider, QFont.Weight.Bold)
        countdown_font = QFont("Times", self._config.starter_font_countdown, QFont.Weight.Bold)
        clock_font = QFont("Times", self._config.starter_font_clock, QFont.Weight.Bold)

        # Track vertical position
        y_cursor = 0

        # --- Logo (top-right corner) ---
        if self._logo and not self._logo.isNull():
            # Scale logo to fit within 15% of window height, maintaining aspect ratio
            max_logo_h = int(h * 0.15)
            scaled = self._logo.scaledToHeight(max_logo_h, Qt.TransformationMode.SmoothTransformation)
            logo_x = w - scaled.width() - 15
            logo_y = 10
            painter.drawPixmap(logo_x, logo_y, scaled)

        # --- Race title (top center) ---
        if self._config.race_title:
            painter.setFont(title_font)
            fm_title = painter.fontMetrics()
            text_w = fm_title.horizontalAdvance(self._config.race_title)
            cx = (w - text_w) // 2
            y_cursor = int(fm_title.height() * 1.1)
            painter.drawText(cx, y_cursor, self._config.race_title)
            y_cursor += int(fm_title.height() * 0.3)  # spacing after title

        # --- Rider name ---
        painter.setFont(rider_font)
        fm_rider = painter.fontMetrics()

        if self._rider_name:
            text_w = fm_rider.horizontalAdvance(self._rider_name)
            cx = (w - text_w) // 2
            y_cursor += int(fm_rider.height() * 1.1)
            painter.drawText(cx, y_cursor, self._rider_name)
        else:
            # Reserve space even when empty so countdown stays positioned
            y_cursor += int(fm_rider.height() * 1.1)

        # --- Countdown (center, huge) ---
        painter.setFont(countdown_font)
        fm_countdown = painter.fontMetrics()

        if self._countdown:
            text_w = fm_countdown.horizontalAdvance(self._countdown)
            cx = (w - text_w) // 2
            # ascent() gives the distance from baseline to top of tallest glyph
            # Place so the top of the digits sits just below y_cursor
            y_cursor += fm_countdown.ascent()
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
