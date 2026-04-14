"""Tests for PersistenceService."""

from datetime import datetime
from pathlib import Path

import pytest

from timetrial.models.rider import Rider
from timetrial.models.race import Race, RaceState
from timetrial.services.persistence_service import PersistenceService


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "test_races.db"


@pytest.fixture
def svc(db_path) -> PersistenceService:
    s = PersistenceService(db_path)
    s.open()
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

class TestCreateAndLoad:
    def test_create_race(self, svc):
        race_id = svc.create_race()
        assert race_id is not None
        assert race_id > 0
        assert svc.current_race_id == race_id

    def test_save_and_load_riders(self, svc):
        race_id = svc.create_race()
        riders = [
            Rider("1", "Smith", "John", "Cat A", 0.5),
            Rider("2", "Jones", "Jane", "Cat B", 1.0),
        ]
        svc.save_riders(riders)

        data = svc.load_race(race_id)
        assert len(data["riders"]) == 2
        assert data["riders"][0].bib_number == "1"
        assert data["riders"][0].start_position == 0.5
        assert data["riders"][1].last_name == "Jones"

    def test_save_and_load_finish_records(self, svc):
        race_id = svc.create_race()
        svc.save_riders([Rider("1", "A", "B", "Cat", 0.5)])
        svc.save_finish_records([
            ("1", "18:24:30.000", "00:24:00.000"),
            ("2", "18:25:00.000", "00:23:00.000"),
        ])

        data = svc.load_race(race_id)
        assert len(data["finish_records"]) == 2
        assert data["finish_records"][0] == ("1", "18:24:30.000", "00:24:00.000")
        assert data["finish_records"][1] == ("2", "18:25:00.000", "00:23:00.000")

    def test_update_race_state(self, svc):
        race_id = svc.create_race()
        start_time = datetime(2024, 7, 20, 18, 0, 0)
        svc.update_race_state(RaceState.RUNNING, start_time)

        data = svc.load_race(race_id)
        assert data["state"] == RaceState.RUNNING
        assert data["start_time"] == start_time

    def test_load_nonexistent_race_raises(self, svc):
        with pytest.raises(ValueError, match="not found"):
            svc.load_race(9999)

    def test_riders_sorted_by_position(self, svc):
        svc.create_race()
        riders = [
            Rider("3", "C", "D", "Cat", 1.5),
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("2", "E", "F", "Cat", 1.0),
        ]
        svc.save_riders(riders)

        data = svc.load_race(svc.current_race_id)
        positions = [r.start_position for r in data["riders"]]
        assert positions == [0.5, 1.0, 1.5]


# ---------------------------------------------------------------------------
# Auto-save
# ---------------------------------------------------------------------------

class TestAutoSave:
    def test_auto_save_creates_race_if_needed(self, svc):
        assert svc.current_race_id is None

        race = Race()
        race.state = RaceState.RUNNING
        race.start_time = datetime(2024, 7, 20, 18, 0, 0)
        race.riders = [Rider("1", "A", "B", "Cat", 0.5)]

        svc.auto_save(race, [("1", "18:24:30.000", "00:24:00.000")])

        assert svc.current_race_id is not None
        data = svc.load_race(svc.current_race_id)
        assert data["state"] == RaceState.RUNNING
        assert len(data["riders"]) == 1
        assert len(data["finish_records"]) == 1

    def test_auto_save_replaces_data(self, svc):
        race = Race()
        race.state = RaceState.RUNNING
        race.riders = [Rider("1", "A", "B", "Cat", 0.5)]

        # First save
        svc.auto_save(race, [])

        # Add a finish and save again
        svc.auto_save(race, [("1", "18:24:30.000", "00:24:00.000")])

        data = svc.load_race(svc.current_race_id)
        assert len(data["finish_records"]) == 1  # replaced, not appended

    def test_auto_save_updates_riders(self, svc):
        race = Race()
        race.state = RaceState.NOT_STARTED
        race.riders = [Rider("1", "A", "B", "Cat", 0.5)]

        svc.auto_save(race, [])

        # Add another rider
        race.riders.append(Rider("2", "C", "D", "Cat", 1.0))
        svc.auto_save(race, [])

        data = svc.load_race(svc.current_race_id)
        assert len(data["riders"]) == 2


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

class TestRecovery:
    def test_find_recoverable_running(self, svc):
        svc.create_race()
        svc.update_race_state(RaceState.RUNNING)

        found = svc.find_recoverable_race()
        assert found == svc.current_race_id

    def test_find_recoverable_not_started(self, svc):
        svc.create_race()
        # Default state is NOT_STARTED
        found = svc.find_recoverable_race()
        assert found == svc.current_race_id

    def test_no_recoverable_when_stopped(self, svc):
        svc.create_race()
        svc.update_race_state(RaceState.STOPPED)

        found = svc.find_recoverable_race()
        assert found is None

    def test_mark_completed_clears_current(self, svc):
        svc.create_race()
        svc.update_race_state(RaceState.RUNNING)
        svc.mark_race_completed()

        assert svc.current_race_id is None
        assert svc.find_recoverable_race() is None

    def test_recovers_most_recent(self, svc):
        # Create two races, leave second one running
        id1 = svc.create_race()
        svc.update_race_state(RaceState.STOPPED)

        id2 = svc.create_race()
        svc.update_race_state(RaceState.RUNNING)

        found = svc.find_recoverable_race()
        assert found == id2

    def test_full_recovery_round_trip(self, svc):
        """Simulate a crash: save state, close, reopen, recover."""
        race = Race()
        race.state = RaceState.RUNNING
        race.start_time = datetime(2024, 7, 20, 18, 0, 0)
        race.riders = [
            Rider("1", "Smith", "John", "Cat A", 0.5),
            Rider("2", "Jones", "Jane", "Cat B", 1.0),
        ]

        svc.auto_save(race, [
            ("1", "18:24:30.000", "00:24:00.000"),
        ])
        race_id = svc.current_race_id

        # "Crash" — close and reopen
        svc.close()
        svc.open()

        # Should find the recoverable race
        found = svc.find_recoverable_race()
        assert found == race_id

        # Load it
        data = svc.load_race(found)
        assert data["state"] == RaceState.RUNNING
        assert data["start_time"] == datetime(2024, 7, 20, 18, 0, 0)
        assert len(data["riders"]) == 2
        assert data["riders"][0].bib_number == "1"
        assert len(data["finish_records"]) == 1
        assert data["finish_records"][0] == ("1", "18:24:30.000", "00:24:00.000")


# ---------------------------------------------------------------------------
# List races
# ---------------------------------------------------------------------------

class TestListRaces:
    def test_empty_db(self, svc):
        assert svc.list_races() == []

    def test_lists_races(self, svc):
        svc.create_race()
        svc.create_race()

        races = svc.list_races()
        assert len(races) == 2
        # Most recent first
        assert races[0]["race_id"] > races[1]["race_id"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_save_with_no_current_race(self, svc):
        """save_riders/save_finish_records should be no-ops without a race."""
        svc.save_riders([Rider("1", "A", "B", "Cat", 0.5)])  # no crash
        svc.save_finish_records([("1", "18:00:00.000", "00:20:00.000")])  # no crash

    def test_placeholder_riders_saved(self, svc):
        svc.create_race()
        riders = [
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("----", "----", "----", "----", 1.0),
        ]
        svc.save_riders(riders)

        data = svc.load_race(svc.current_race_id)
        assert len(data["riders"]) == 2
        assert data["riders"][1].is_placeholder

    def test_db_created_in_new_directory(self, tmp_path):
        """DB path with non-existent parent directory should be created."""
        db_path = tmp_path / "subdir" / "deep" / "races.db"
        s = PersistenceService(db_path)
        s.open()
        s.create_race()
        s.close()
        assert db_path.exists()
