"""Tests for TimingService and EventBus."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from timetrial.config.settings import load_config
from timetrial.models.rider import Rider
from timetrial.models.race import Race, RaceState
from timetrial.services.event_bus import EventBus
from timetrial.services.timing_service import TimingService


# Ensure a QApplication exists for the test session
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def config():
    return load_config(user_path=Path("/nonexistent"))


@pytest.fixture
def event_bus(qapp):
    return EventBus()


@pytest.fixture
def race_with_riders():
    race = Race()
    race.riders = [
        Rider("1", "Smith", "John", "Cat A", 0.5),
        Rider("2", "Jones", "Jane", "Cat B", 1.0),
        Rider("3", "Brown", "Bob", "Cat A", 1.5),
    ]
    return race


@pytest.fixture
def timing_svc(race_with_riders, config, event_bus):
    return TimingService(race_with_riders, config, event_bus)


# ---------------------------------------------------------------------------
# Start / Stop
# ---------------------------------------------------------------------------

class TestStartStop:
    def test_start_sets_state(self, timing_svc, race_with_riders):
        timing_svc.start_race()
        assert race_with_riders.state == RaceState.RUNNING
        assert race_with_riders.start_time is not None
        assert race_with_riders.current_rider_index == 0
        assert timing_svc.is_running is True
        timing_svc.stop_race()

    def test_stop_sets_state(self, timing_svc, race_with_riders):
        timing_svc.start_race()
        timing_svc.stop_race()
        assert race_with_riders.state == RaceState.STOPPED
        assert timing_svc.is_running is False

    def test_start_emits_race_started(self, timing_svc, event_bus):
        handler = MagicMock()
        event_bus.race_started.connect(handler)
        timing_svc.start_race()
        handler.assert_called_once()
        timing_svc.stop_race()

    def test_stop_emits_race_stopped(self, timing_svc, event_bus):
        handler = MagicMock()
        event_bus.race_stopped.connect(handler)
        timing_svc.start_race()
        timing_svc.stop_race()
        handler.assert_called_once()

    def test_start_emits_initial_rider_status(self, timing_svc, event_bus):
        on_ramp = MagicMock()
        on_deck = MagicMock()
        in_hole = MagicMock()
        event_bus.rider_on_ramp.connect(on_ramp)
        event_bus.rider_on_deck.connect(on_deck)
        event_bus.rider_in_hole.connect(in_hole)

        timing_svc.start_race()

        on_ramp.assert_called_once_with("John Smith", "1")
        on_deck.assert_called_once_with("Jane Jones")
        in_hole.assert_called_once_with("Bob Brown")

        timing_svc.stop_race()

    def test_set_start_time(self, timing_svc, race_with_riders):
        custom_time = datetime(2024, 7, 20, 18, 0, 0)
        timing_svc.set_start_time(custom_time)
        assert race_with_riders.start_time == custom_time


# ---------------------------------------------------------------------------
# Elapsed time
# ---------------------------------------------------------------------------

class TestElapsed:
    def test_elapsed_zero_before_start(self, timing_svc):
        assert timing_svc.elapsed_ms == 0

    def test_elapsed_after_start(self, timing_svc):
        timing_svc.start_race()
        # elapsed should be very small (< 100ms)
        assert 0 <= timing_svc.elapsed_ms < 500
        timing_svc.stop_race()


# ---------------------------------------------------------------------------
# Timer callback (deterministic via _on_timeout)
# ---------------------------------------------------------------------------

class TestOnTimeout:
    def test_emits_elapsed_updated(self, timing_svc, race_with_riders, event_bus):
        handler = MagicMock()
        event_bus.elapsed_updated.connect(handler)

        race_with_riders.start_time = datetime.now() - timedelta(seconds=5)
        race_with_riders.state = RaceState.RUNNING
        race_with_riders.current_rider_index = 0

        timing_svc._on_timeout()

        handler.assert_called_once()
        elapsed_ms = handler.call_args[0][0]
        assert 4500 < elapsed_ms < 6000  # ~5 seconds

    def test_emits_countdown_positive(self, timing_svc, race_with_riders, event_bus):
        """When rider's start is in the future, countdown should be positive."""
        handler = MagicMock()
        event_bus.countdown_updated.connect(handler)

        # Race started just now, rider at 0.5 min = 30 seconds in future
        race_with_riders.start_time = datetime.now()
        race_with_riders.current_rider_index = 0

        timing_svc._on_timeout()

        handler.assert_called_once()
        countdown = handler.call_args[0][0]
        assert 29.0 < countdown < 31.0  # ~30 seconds

    def test_rider_advances_on_negative_countdown(self, timing_svc, race_with_riders, event_bus):
        """When countdown goes negative, rider index should advance."""
        advanced = MagicMock()
        event_bus.rider_advanced.connect(advanced)

        # Race started 2 minutes ago, rider 0 at 0.5 min should have started already
        race_with_riders.start_time = datetime.now() - timedelta(minutes=2)
        race_with_riders.current_rider_index = 0

        timing_svc._on_timeout()

        advanced.assert_called_once()
        assert race_with_riders.current_rider_index == 1

    def test_rider_status_updated_on_advance(self, timing_svc, race_with_riders, event_bus):
        """When advancing, should emit new on-ramp/on-deck/in-hole."""
        on_ramp = MagicMock()
        on_deck = MagicMock()
        in_hole = MagicMock()
        event_bus.rider_on_ramp.connect(on_ramp)
        event_bus.rider_on_deck.connect(on_deck)
        event_bus.rider_in_hole.connect(in_hole)

        race_with_riders.start_time = datetime.now() - timedelta(minutes=2)
        race_with_riders.current_rider_index = 0

        timing_svc._on_timeout()

        # After advancing to rider index 1:
        on_ramp.assert_called_with("Jane Jones", "2")
        on_deck.assert_called_with("Bob Brown")
        in_hole.assert_called_with("")  # No rider at index 3

    def test_all_riders_started_signal(self, timing_svc, race_with_riders, event_bus):
        """When last rider starts, all_riders_started should emit."""
        all_started = MagicMock()
        event_bus.all_riders_started.connect(all_started)

        # Race started long ago, currently on last rider
        race_with_riders.start_time = datetime.now() - timedelta(minutes=10)
        race_with_riders.current_rider_index = 2  # last rider (index 2 of 3)

        timing_svc._on_timeout()

        all_started.assert_called_once()
        assert race_with_riders.current_rider_index == 3  # past end


# ---------------------------------------------------------------------------
# Sound trigger
# ---------------------------------------------------------------------------

class TestSoundTrigger:
    def test_fires_once_per_rider(self, timing_svc, race_with_riders, event_bus):
        """Sound trigger should fire exactly once when countdown <= threshold."""
        handler = MagicMock()
        event_bus.countdown_sound_trigger.connect(handler)

        # Rider 0 at 0.5 min (30s). Race started 20 seconds ago → countdown ~10s (at threshold of 11s)
        race_with_riders.start_time = datetime.now() - timedelta(seconds=20)
        race_with_riders.current_rider_index = 0
        timing_svc._sound_armed = True

        timing_svc._on_timeout()
        assert handler.call_count == 1

        # Second tick should NOT fire again (sound_armed is now False)
        timing_svc._on_timeout()
        assert handler.call_count == 1

    def test_rearms_after_rider_advance(self, timing_svc, race_with_riders, event_bus):
        """Sound should rearm when advancing to next rider."""
        handler = MagicMock()
        event_bus.countdown_sound_trigger.connect(handler)

        # Rider already started (negative countdown) → will advance
        race_with_riders.start_time = datetime.now() - timedelta(minutes=2)
        race_with_riders.current_rider_index = 0
        timing_svc._sound_armed = False  # was already fired

        timing_svc._on_timeout()

        # After advancing, sound_armed should be True again
        assert timing_svc._sound_armed is True

    def test_no_trigger_above_threshold(self, timing_svc, race_with_riders, event_bus):
        """Sound should NOT fire when countdown > threshold."""
        handler = MagicMock()
        event_bus.countdown_sound_trigger.connect(handler)

        # Rider 0 at 0.5 min. Race just started → countdown ~30s (above 16s threshold)
        race_with_riders.start_time = datetime.now()
        race_with_riders.current_rider_index = 0

        timing_svc._on_timeout()

        handler.assert_not_called()


# ---------------------------------------------------------------------------
# Record finish
# ---------------------------------------------------------------------------

class TestRecordFinish:
    def test_returns_current_datetime(self, timing_svc):
        before = datetime.now()
        finish_time = timing_svc.record_finish()
        after = datetime.now()
        assert before <= finish_time <= after


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_riders(self, config, event_bus, qapp):
        """Should handle empty rider list gracefully."""
        race = Race()
        race.riders = []
        svc = TimingService(race, config, event_bus)

        race.start_time = datetime.now()
        race.current_rider_index = 0

        # Should not raise
        svc._on_timeout()

    def test_no_start_time(self, timing_svc, race_with_riders, event_bus):
        """Should handle None start_time gracefully."""
        handler = MagicMock()
        event_bus.elapsed_updated.connect(handler)

        race_with_riders.start_time = None

        # Should not raise
        timing_svc._on_timeout()
        handler.assert_not_called()

    def test_two_rider_race(self, config, event_bus, qapp):
        """Only 2 riders: in-hole should be empty from the start."""
        race = Race()
        race.riders = [
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("2", "C", "D", "Cat", 1.0),
        ]
        svc = TimingService(race, config, event_bus)

        in_hole = MagicMock()
        event_bus.rider_in_hole.connect(in_hole)

        svc.start_race()
        in_hole.assert_called_with("")  # no rider at index 2
        svc.stop_race()
