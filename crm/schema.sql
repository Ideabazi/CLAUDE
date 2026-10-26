-- Ideabazi outreach CRM schema (SQLite)

CREATE TABLE IF NOT EXISTS contacts (
    id                TEXT PRIMARY KEY,          -- li-0001
    first_name        TEXT,
    last_name         TEXT,
    title             TEXT,
    company           TEXT,
    company_domain    TEXT,
    linkedin_url      TEXT UNIQUE,
    email             TEXT,
    email_status      TEXT,                      -- verified | inferred
    location          TEXT,
    country           TEXT,
    employees         INTEGER,
    industry          TEXT,
    degree            INTEGER,                   -- 1 | 2 | 3
    connected_on      TEXT,
    mutuals           TEXT,                      -- count + up to 2 names (never named to prospect)
    warm_path         TEXT,                      -- e.g. "intro via <mutual>"
    recent_activity   TEXT,                      -- dated post/comment topic
    source            TEXT,                      -- linkedin_export | salesnav | apollo | clay | research
    route             TEXT,                      -- obdg | aiweb (config/outreach.toml)
    campaign          TEXT,
    is_decision_maker INTEGER,
    disq_reason       TEXT,
    -- score out of 25 (5 each)
    fit               INTEGER DEFAULT 0,
    signal            INTEGER DEFAULT 0,
    pain              INTEGER DEFAULT 0,
    reach             INTEGER DEFAULT 0,
    capacity          INTEGER DEFAULT 0,
    signal_note       TEXT,                      -- dated + sourced
    pain_note         TEXT,
    gift              TEXT,
    icebreaker_a      TEXT,
    icebreaker_b      TEXT,
    icebreaker_choice TEXT,                      -- A | B (for A/B measurement)
    -- pipeline
    stage             TEXT NOT NULL DEFAULT 'new',
    sequence          TEXT,
    seq_started       TEXT,                      -- date the sequence began
    step              INTEGER DEFAULT 0,         -- next step index in the sequence
    next_touch_due    TEXT,
    last_touch_at     TEXT,
    notes             TEXT,
    researched_at     TEXT,
    created_at        TEXT,
    updated_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_contacts_stage ON contacts(stage);
CREATE INDEX IF NOT EXISTS idx_contacts_due ON contacts(next_touch_due);

-- Drafted copy, one per sequence step
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL REFERENCES contacts(id),
    step       INTEGER NOT NULL,
    channel    TEXT NOT NULL,
    subject    TEXT,
    body       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'draft',   -- draft | approved | sent
    created_at TEXT,
    UNIQUE (contact_id, step)
);

-- Every event: sends, accepts, replies, meetings, outcomes
CREATE TABLE IF NOT EXISTS touches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL REFERENCES contacts(id),
    ts         TEXT NOT NULL,
    channel    TEXT,
    event      TEXT NOT NULL,                   -- sent | accepted | replied | booked | held | proposal | won | lost | ...
    step       INTEGER,
    variant    TEXT,
    sentiment  TEXT,
    detail     TEXT
);

CREATE INDEX IF NOT EXISTS idx_touches_contact ON touches(contact_id);
CREATE INDEX IF NOT EXISTS idx_touches_day ON touches(ts);
