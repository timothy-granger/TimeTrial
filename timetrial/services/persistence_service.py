"""SQLite persistence — auto-save race state and crash recovery."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from timetrial.models.rider import Rider
from timetrial.models.race import Race, RaceState
from timetrial.models.result import NO_RESULT_SENTINEL


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    race_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time  TEXT,
    state       TEXT NOT NULL DEFAULT 'NOT_STARTED',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS riders (
    rider_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    bib_number      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    first_name      TEXT NOT NULL,
    category        TEXT NOT NULL,
    start_position  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS finish_records (
    finish_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id         INTEGER NOT NULL REFERENCES races(race_id),
    bib             TEXT NOT NULL,
    finish_time_str TEXT NOT NULL,
    result_str      TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PersistenceService:
    """SQLite storage for races, riders, and finish records."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._current_race_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open the database and create tables if needed."""
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def current_race_id(self) -> Optional[int]:
        return self._current_race_id

    # ------------------------------------------------------------------
    # Race lifecycle
    # ------------------------------------------------------------------

    def create_race(self) -> int:
        """Create a new race record. Returns the race_id."""
        now = _now_str()
        cur = self._conn.execute(
            "INSERT INTO races (state, created_at, updated_at) VALUES (?, ?, ?)",
            (RaceState.NOT_STARTED.name, now, now),
        )
        self._conn.commit()
        self._current_race_id = cur.lastrowid
        return self._current_race_id

    def update_race_state(self, state: RaceState, start_time: Optional[datetime] = None) -> None:
        """Update the current race's state and optionally its start_time."""
        if self._current_race_id is None:
            return
        start_str = start_time.isoformat() if start_time else None
        self._conn.execute(
            "UPDATE races SET state=?, start_time=?, updated_at=? WHERE race_id=?",
            (state.name, start_str, _now_str(), self._current_race_id),
        )
        self._conn.commit()

    def mark_race_completed(self) -> None:
        """Mark the current race as stopped/completed."""
        self.update_race_state(RaceState.STOPPED)
        self._current_race_id = None

    # ------------------------------------------------------------------
    # Riders
    # ------------------------------------------------------------------

    def save_riders(self, riders: list[Rider], race_id: Optional[int] = None) -> None:
        """Save/replace all riders for a race."""
        rid = race_id or self._current_race_id
        if rid is None:
            return

        self._conn.execute("DELETE FROM riders WHERE race_id=?", (rid,))
        self._conn.executemany(
            "INSERT INTO riders (race_id, bib_number, last_name, first_name, category, start_position) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(rid, r.bib_number, r.last_name, r.first_name, r.category, r.start_position)
             for r in riders],
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Finish records
    # ------------------------------------------------------------------

    def save_finish_records(
        self,
        finish_rows: list[tuple[str, str, str]],
        race_id: Optional[int] = None,
    ) -> None:
        """Save/replace all finish records for a race.

        Each row is (bib, finish_time_str, result_str).
        """
        rid = race_id or self._current_race_id
        if rid is None:
            return

        self._conn.execute("DELETE FROM finish_records WHERE race_id=?", (rid,))
        self._conn.executemany(
            "INSERT INTO finish_records (race_id, bib, finish_time_str, result_str) "
            "VALUES (?, ?, ?, ?)",
            [(rid, bib, finish, result) for bib, finish, result in finish_rows],
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Auto-save (full snapshot)
    # ------------------------------------------------------------------

    def auto_save(
        self,
        race: Race,
        finish_rows: list[tuple[str, str, str]],
    ) -> None:
        """Save a full snapshot of the current race state.

        Called after each significant event (start, finish recorded, import).
        """
        if self._current_race_id is None:
            self.create_race()

        self.update_race_state(
            race.state,
            race.start_time,
        )
        self.save_riders(race.riders)
        self.save_finish_records(finish_rows)

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def find_recoverable_race(self) -> Optional[int]:
        """Find a race that was NOT_STARTED or RUNNING (i.e. not cleanly stopped).

        Returns the race_id or None.
        """
        cur = self._conn.execute(
            "SELECT race_id FROM races WHERE state IN (?, ?) ORDER BY race_id DESC LIMIT 1",
            (RaceState.NOT_STARTED.name, RaceState.RUNNING.name),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def load_race(self, race_id: int) -> dict:
        """Load a full race snapshot.

        Returns a dict with keys:
            'start_time': Optional[datetime],
            'state': RaceState,
            'riders': list[Rider],
            'finish_records': list[tuple[str, str, str]],  # (bib, finish_time, result)
        """
        # Race metadata
        cur = self._conn.execute(
            "SELECT start_time, state FROM races WHERE race_id=?", (race_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Race {race_id} not found")

        start_time_str, state_str = row
        start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
        state = RaceState[state_str]

        # Riders
        cur = self._conn.execute(
            "SELECT bib_number, last_name, first_name, category, start_position "
            "FROM riders WHERE race_id=? ORDER BY start_position",
            (race_id,),
        )
        riders = [
            Rider(bib, last, first, cat, pos)
            for bib, last, first, cat, pos in cur.fetchall()
        ]

        # Finish records
        cur = self._conn.execute(
            "SELECT bib, finish_time_str, result_str "
            "FROM finish_records WHERE race_id=? ORDER BY finish_id",
            (race_id,),
        )
        finish_records = cur.fetchall()

        self._current_race_id = race_id

        return {
            "start_time": start_time,
            "state": state,
            "riders": riders,
            "finish_records": [(bib, ft, res) for bib, ft, res in finish_records],
        }

    def list_races(self) -> list[dict]:
        """List all races with basic info."""
        cur = self._conn.execute(
            "SELECT race_id, start_time, state, created_at FROM races ORDER BY race_id DESC"
        )
        return [
            {
                "race_id": rid,
                "start_time": st,
                "state": state,
                "created_at": created,
            }
            for rid, st, state, created in cur.fetchall()
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_str() -> str:
    return datetime.now().isoformat()
