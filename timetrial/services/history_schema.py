"""Extended SQLite schema for historical race data and cross-race queries."""

HISTORY_SCHEMA = """
-- Master rider identity (one row per unique person)
CREATE TABLE IF NOT EXISTS riders_master (
    rider_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    UNIQUE(first_name, last_name)
);

-- Race events with metadata
CREATE TABLE IF NOT EXISTS race_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name  TEXT NOT NULL DEFAULT 'Greenville Spinners Time Trial',
    event_date  TEXT NOT NULL,           -- ISO date: 2022-07-28
    course      TEXT NOT NULL DEFAULT 'Standard',
    notes       TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL DEFAULT '',  -- CSV file this was imported from
    UNIQUE(event_date, event_name)
);

-- Race entries: who raced in which event, with what bib/category
CREATE TABLE IF NOT EXISTS race_entries (
    entry_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        INTEGER NOT NULL REFERENCES race_events(event_id),
    rider_id        INTEGER NOT NULL REFERENCES riders_master(rider_id),
    bib_number      TEXT NOT NULL,
    category        TEXT NOT NULL,
    start_position  REAL NOT NULL DEFAULT 0,
    UNIQUE(event_id, rider_id)
);

-- Race results: calculated finish data
CREATE TABLE IF NOT EXISTS race_results (
    result_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        INTEGER NOT NULL REFERENCES race_events(event_id),
    entry_id        INTEGER NOT NULL REFERENCES race_entries(entry_id),
    rider_id        INTEGER NOT NULL REFERENCES riders_master(rider_id),
    finish_time_str TEXT NOT NULL,       -- wall-clock "hh:mm:ss.zzz"
    result_time_str TEXT NOT NULL,       -- elapsed "hh:mm:ss.zzz"
    result_ms       INTEGER NOT NULL,    -- elapsed in ms for sorting
    category        TEXT NOT NULL,
    category_place  INTEGER,             -- 1st, 2nd, 3rd within category
    overall_place   INTEGER,             -- overall ranking (juniors excluded)
    UNIQUE(event_id, rider_id)
);

-- Category name normalization map
CREATE TABLE IF NOT EXISTS category_map (
    raw_name        TEXT PRIMARY KEY,
    canonical_name  TEXT NOT NULL
);

-- Name normalization map (for merging duplicates)
CREATE TABLE IF NOT EXISTS name_map (
    raw_first       TEXT NOT NULL,
    raw_last        TEXT NOT NULL,
    canonical_first TEXT NOT NULL,
    canonical_last  TEXT NOT NULL,
    PRIMARY KEY(raw_first, raw_last)
);

-- Useful views
CREATE VIEW IF NOT EXISTS v_rider_history AS
SELECT
    rm.rider_id,
    rm.first_name,
    rm.last_name,
    re.event_date,
    re.event_name,
    rr.category,
    rr.result_time_str,
    rr.result_ms,
    rr.category_place,
    rr.overall_place
FROM race_results rr
JOIN riders_master rm ON rm.rider_id = rr.rider_id
JOIN race_events re ON re.event_id = rr.event_id
ORDER BY rm.last_name, rm.first_name, re.event_date;

CREATE VIEW IF NOT EXISTS v_category_winners AS
SELECT
    re.event_date,
    rr.category,
    rm.first_name,
    rm.last_name,
    rr.result_time_str,
    rr.result_ms
FROM race_results rr
JOIN riders_master rm ON rm.rider_id = rr.rider_id
JOIN race_events re ON re.event_id = rr.event_id
WHERE rr.category_place = 1
ORDER BY re.event_date, rr.category;

CREATE VIEW IF NOT EXISTS v_personal_bests AS
SELECT
    rm.rider_id,
    rm.first_name,
    rm.last_name,
    rr.category,
    MIN(rr.result_ms) AS best_ms,
    rr.result_time_str AS best_time,
    re.event_date AS best_date
FROM race_results rr
JOIN riders_master rm ON rm.rider_id = rr.rider_id
JOIN race_events re ON re.event_id = rr.event_id
GROUP BY rm.rider_id, rr.category
ORDER BY rm.last_name, rm.first_name;
"""
