-- ora — SQLite schema
--
-- subjects: people (clone members) and entities (clone itself)
-- saju_pillars: computed 사주 four pillars
-- natal_chart: computed Western natal placements
-- readings: log of every reading ora has given (for memory / continuity)

CREATE TABLE IF NOT EXISTS subjects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kind            TEXT    NOT NULL CHECK (kind IN ('person', 'entity')),
    slack_user_id   TEXT    UNIQUE,                -- NULL for entities like clone
    display_name    TEXT    NOT NULL,
    birth_date      TEXT    NOT NULL,              -- ISO 8601 date (YYYY-MM-DD)
    birth_time      TEXT,                          -- HH:MM, NULL if unknown
    birth_tz        TEXT    NOT NULL,              -- IANA tz name, e.g. 'Asia/Seoul'
    birth_place     TEXT    NOT NULL,              -- human-readable
    birth_lat       REAL,
    birth_lon       REAL,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subjects_slack_user
    ON subjects(slack_user_id) WHERE slack_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS saju_pillars (
    subject_id      INTEGER PRIMARY KEY REFERENCES subjects(id) ON DELETE CASCADE,
    year_pillar     TEXT,                          -- e.g. '丙午'
    month_pillar    TEXT,                          -- e.g. '庚寅'
    day_pillar      TEXT,
    hour_pillar     TEXT,                          -- NULL if birth_time unknown
    day_master      TEXT,                          -- 일간, e.g. '癸'
    elements_json   TEXT,                          -- 오행 balance counts as JSON
    notes           TEXT,
    computed_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS natal_chart (
    subject_id      INTEGER PRIMARY KEY REFERENCES subjects(id) ON DELETE CASCADE,
    placements_json TEXT,                          -- planets/signs/degrees/houses as JSON
    ascendant       TEXT,                          -- NULL if no birth_time
    house_system    TEXT,                          -- e.g. 'whole_sign'
    notes           TEXT,
    computed_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS readings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id        INTEGER REFERENCES subjects(id),    -- NULL for anonymous interactions
    surface           TEXT    NOT NULL,                   -- daily_post|channel_mention|thread_reply|dm|huddle_thread
    slack_channel_id  TEXT,
    slack_thread_ts   TEXT,
    slack_message_ts  TEXT,
    question          TEXT,
    response          TEXT    NOT NULL,
    model             TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_readings_subject ON readings(subject_id);
CREATE INDEX IF NOT EXISTS idx_readings_thread  ON readings(slack_channel_id, slack_thread_ts);
CREATE INDEX IF NOT EXISTS idx_readings_created ON readings(created_at);
