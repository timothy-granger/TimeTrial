"""Shared test fixtures."""

import pytest
from timetrial.models.rider import Rider
from timetrial.models.race import Race, FinishRecord
from datetime import datetime


@pytest.fixture
def sample_rider() -> Rider:
    return Rider(
        bib_number="42",
        last_name="Merckx",
        first_name="Eddy",
        category="Men (P/1/2/3)",
        start_position=1.0,
    )


@pytest.fixture
def sample_riders() -> list[Rider]:
    return [
        Rider("1", "Smith", "John", "Men (4/5/U)", 0.5),
        Rider("2", "Jones", "Jane", "Women (P/1/2/3)", 1.0),
        Rider("3", "Brown", "Bob", "Men (P/1/2/3)", 1.5),
        Rider("4", "Davis", "Amy", "10-14 (F)", 2.0),
    ]


@pytest.fixture
def sample_race(sample_riders) -> Race:
    race = Race()
    race.riders = sample_riders
    race.start_time = datetime(2024, 7, 20, 18, 0, 0)
    return race
