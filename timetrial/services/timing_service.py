"""Race clock, countdown, and rider start sequencing."""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer

from timetrial.config.settings import AppConfig
from timetrial.models.race import Race, RaceState
from timetrial.services.event_bus import EventBus


class TimingService(QObject):
    """Owns the QTimer. Computes elapsed time, countdown per rider,
    advances the rider sequence, and emits events via the EventBus.

    Contains zero UI code.
    """

    def __init__(
        self,
        race: Race,
        config: AppConfig,
        event_bus: EventBus,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._race = race
        self._config = config
        self._bus = event_bus

        self._timer = QTimer(self)
        self._timer.setInterval(config.timer_interval_ms)
        self._timer.timeout.connect(self._on_timeout)

        # Sound trigger: fire once per rider when countdown <= threshold
        self._sound_armed = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_race(self) -> None:
        """Capture start time = now, begin the timer, emit initial events."""
        self._race.start_time = datetime.now()
        self._race.state = RaceState.RUNNING
        self._race.current_rider_index = 0
        self._sound_armed = True

        self._timer.start()
        self._bus.race_started.emit()

        # Emit initial rider info
        self._emit_rider_status()

    def stop_race(self) -> None:
        """Stop the timer."""
        self._timer.stop()
        self._race.state = RaceState.STOPPED
        self._bus.race_stopped.emit()

    def set_start_time(self, dt: datetime) -> None:
        """Manual override of the race start time (pre-race correction)."""
        self._race.start_time = dt

    @property
    def is_running(self) -> bool:
        return self._race.state == RaceState.RUNNING

    @property
    def elapsed_ms(self) -> int:
        if self._race.start_time is None:
            return 0
        delta = datetime.now() - self._race.start_time
        return int(delta.total_seconds() * 1000)

    def record_finish(self) -> datetime:
        """Capture the current time as a finish timestamp.

        Returns the captured datetime so callers can create a FinishRecord.
        """
        return datetime.now()

    # ------------------------------------------------------------------
    # Timer callback
    # ------------------------------------------------------------------

    def _on_timeout(self) -> None:
        """Called every timer_interval_ms. Computes elapsed, countdown,
        advances rider when countdown goes negative."""
        now = datetime.now()
        start = self._race.start_time
        if start is None:
            return

        # Elapsed since race start
        elapsed_ms = int((now - start).total_seconds() * 1000)
        self._bus.elapsed_updated.emit(elapsed_ms)

        # Current rider countdown
        riders = self._race.riders
        idx = self._race.current_rider_index
        if idx >= len(riders):
            return

        rider = riders[idx]
        rider_start_dt = start + timedelta(milliseconds=rider.start_offset_ms)
        countdown_sec = (rider_start_dt - now).total_seconds()

        # Sound trigger: fire once when countdown <= threshold
        if countdown_sec <= self._config.countdown_sound_trigger_seconds and self._sound_armed:
            self._sound_armed = False
            self._bus.countdown_sound_trigger.emit()

        if countdown_sec >= 0:
            self._bus.countdown_updated.emit(countdown_sec)
        else:
            # Rider has started — advance to next
            self._sound_armed = True
            self._race.current_rider_index += 1

            if self._race.current_rider_index < len(riders):
                self._emit_rider_status()

                # Recalculate countdown for new rider
                new_rider = riders[self._race.current_rider_index]
                new_start_dt = start + timedelta(milliseconds=new_rider.start_offset_ms)
                new_countdown = (new_start_dt - now).total_seconds()
                self._bus.countdown_updated.emit(new_countdown)
            else:
                # All riders have started
                self._bus.all_riders_started.emit()

            self._bus.rider_advanced.emit(self._race.current_rider_index)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_rider_status(self) -> None:
        """Emit rider-on-ramp / on-deck / in-hole signals."""
        riders = self._race.riders
        idx = self._race.current_rider_index

        if idx < len(riders):
            rider = riders[idx]
            self._bus.rider_on_ramp.emit(rider.display_name, rider.bib_number)
        else:
            self._bus.rider_on_ramp.emit("", "")

        if idx + 1 < len(riders):
            self._bus.rider_on_deck.emit(riders[idx + 1].display_name)
        else:
            self._bus.rider_on_deck.emit("")

        if idx + 2 < len(riders):
            self._bus.rider_in_hole.emit(riders[idx + 2].display_name)
        else:
            self._bus.rider_in_hole.emit("")
