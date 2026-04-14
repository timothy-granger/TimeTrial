"""Tests for data models."""

from datetime import datetime

from timetrial.models.rider import Rider
from timetrial.models.race import Race, RaceState, FinishRecord
from timetrial.models.result import RaceResult, NO_RESULT_SENTINEL
from timetrial.models.series import SeriesEntry


class TestRider:
    def test_display_name(self, sample_rider):
        assert sample_rider.display_name == "Eddy Merckx"

    def test_start_offset_ms_one_minute(self, sample_rider):
        # 1.0 minutes = 60,000 ms
        assert sample_rider.start_offset_ms == 60_000

    def test_start_offset_ms_half_minute(self):
        rider = Rider("1", "A", "B", "Cat", 0.5)
        assert rider.start_offset_ms == 30_000

    def test_start_offset_ms_90_seconds(self):
        rider = Rider("1", "A", "B", "Cat", 1.5)
        assert rider.start_offset_ms == 90_000

    def test_is_placeholder_true(self):
        rider = Rider("----", "", "", "", 0.0)
        assert rider.is_placeholder is True

    def test_is_placeholder_false(self, sample_rider):
        assert sample_rider.is_placeholder is False


class TestFinishRecord:
    def test_identified_with_bib(self):
        fr = FinishRecord(finish_timestamp=datetime.now(), bib_number="42")
        assert fr.is_identified is True

    def test_not_identified_none(self):
        fr = FinishRecord(finish_timestamp=datetime.now())
        assert fr.is_identified is False

    def test_not_identified_empty(self):
        fr = FinishRecord(finish_timestamp=datetime.now(), bib_number="  ")
        assert fr.is_identified is False


class TestRace:
    def test_initial_state(self):
        race = Race()
        assert race.state == RaceState.NOT_STARTED
        assert race.start_time is None
        assert race.riders == []
        assert race.finish_records == []
        assert race.current_rider_index == 0

    def test_rider_by_bib_found(self, sample_race):
        rider = sample_race.rider_by_bib("2")
        assert rider is not None
        assert rider.last_name == "Jones"

    def test_rider_by_bib_not_found(self, sample_race):
        assert sample_race.rider_by_bib("999") is None

    def test_next_start_position_empty(self):
        race = Race()
        assert race.next_start_position(0.5) == 0.5

    def test_next_start_position_gap(self):
        race = Race()
        race.riders = [
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("2", "C", "D", "Cat", 1.0),
            Rider("3", "E", "F", "Cat", 2.0),  # gap at 1.5
        ]
        assert race.next_start_position(0.5) == 1.5

    def test_next_start_position_contiguous(self):
        race = Race()
        race.riders = [
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("2", "C", "D", "Cat", 1.0),
            Rider("3", "E", "F", "Cat", 1.5),
        ]
        assert race.next_start_position(0.5) == 2.0

    def test_insert_rider_sorted_middle(self):
        race = Race()
        race.riders = [
            Rider("1", "A", "B", "Cat", 0.5),
            Rider("3", "E", "F", "Cat", 1.5),
        ]
        new_rider = Rider("2", "C", "D", "Cat", 1.0)
        idx = race.insert_rider_sorted(new_rider)
        assert idx == 1
        assert race.riders[1].bib_number == "2"

    def test_insert_rider_sorted_end(self):
        race = Race()
        race.riders = [Rider("1", "A", "B", "Cat", 0.5)]
        new_rider = Rider("2", "C", "D", "Cat", 1.0)
        idx = race.insert_rider_sorted(new_rider)
        assert idx == 1
        assert len(race.riders) == 2

    def test_insert_rider_sorted_beginning(self):
        race = Race()
        race.riders = [Rider("2", "C", "D", "Cat", 1.0)]
        new_rider = Rider("1", "A", "B", "Cat", 0.5)
        idx = race.insert_rider_sorted(new_rider)
        assert idx == 0
        assert race.riders[0].bib_number == "1"

    def test_is_bib_taken(self, sample_race):
        assert sample_race.is_bib_taken("1") is True
        assert sample_race.is_bib_taken("999") is False

    def test_is_bib_taken_exclude(self, sample_race):
        # Bib "1" exists but excluded (editing that rider)
        assert sample_race.is_bib_taken("1", exclude_bib="1") is False

    def test_is_position_taken(self, sample_race):
        assert sample_race.is_position_taken(0.5) is True
        assert sample_race.is_position_taken(3.0) is False

    def test_is_position_taken_exclude(self, sample_race):
        assert sample_race.is_position_taken(0.5, exclude_bib="1") is False


class TestRaceResult:
    def test_display_name(self):
        r = RaceResult("1", "Eddy", "Merckx", "Cat", "18:22:00.000", "00:22:00.000", 1_320_000)
        assert r.display_name == "Eddy Merckx"

    def test_has_result_true(self):
        r = RaceResult("1", "A", "B", "C", "18:22:00.000", "00:22:00.000", 1_320_000)
        assert r.has_result is True

    def test_has_result_false(self):
        r = RaceResult("1", "A", "B", "C", NO_RESULT_SENTINEL, NO_RESULT_SENTINEL, 0)
        assert r.has_result is False


class TestSeriesEntry:
    def test_display_name(self):
        e = SeriesEntry("Eddy", "Merckx", "Men (P/1/2/3)", 15)
        assert e.display_name == "Eddy Merckx"
