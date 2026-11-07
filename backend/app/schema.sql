-- Assignment 4: SQLite schema. Enable foreign keys for manual use too.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS UserCredentials (
    user_id TEXT PRIMARY KEY NOT NULL CHECK (length(user_id) = 36),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK (length(email) BETWEEN 3 AND 254 AND email = trim(email)
               AND email = lower(email) COLLATE BINARY AND instr(email, '@') > 1),
    password_hash TEXT NOT NULL
        CHECK (length(password_hash) = 60 AND substr(password_hash, 1, 4) = '$2b$'),
    -- Existing API names: patient = User, admin = Administrator.
    role TEXT NOT NULL CHECK (role IN ('patient', 'admin')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS UserProfile (
    email TEXT PRIMARY KEY NOT NULL COLLATE NOCASE
        REFERENCES UserCredentials(email) ON UPDATE CASCADE ON DELETE CASCADE,
    full_name TEXT NOT NULL
        CHECK (length(trim(full_name)) BETWEEN 1 AND 100 AND full_name = trim(full_name)),
    contact_info TEXT CHECK (contact_info IS NULL OR length(contact_info) <= 100),
    preferences TEXT CHECK (preferences IS NULL OR length(preferences) <= 1000)
);

-- Queue tables are STRICT, so SQLite rejects values of the wrong data type.
-- Timestamps are ISO 8601 text; datetime() returns NULL for anything else.

-- Services the clinic offers. Deleting a service archives it (sets deleted_at) instead
-- of removing the row, so past queue entries, history and notifications keep their service.
CREATE TABLE IF NOT EXISTS Service (
    service_id TEXT PRIMARY KEY NOT NULL CHECK (length(service_id) BETWEEN 1 AND 100),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100 AND name = trim(name)),
    description TEXT NOT NULL
        CHECK (length(description) BETWEEN 1 AND 1000 AND description = trim(description)),
    expected_duration_minutes INTEGER NOT NULL CHECK (expected_duration_minutes BETWEEN 1 AND 480),
    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
    created_at TEXT NOT NULL CHECK (datetime(created_at) IS NOT NULL),
    updated_at TEXT NOT NULL CHECK (datetime(updated_at) IS NOT NULL),
    deleted_at TEXT CHECK (deleted_at IS NULL OR datetime(deleted_at) IS NOT NULL)
) STRICT;

-- No two active services share a name (case-insensitive). Archived names can be reused.
CREATE UNIQUE INDEX IF NOT EXISTS Service_active_name ON Service(name COLLATE NOCASE) WHERE deleted_at IS NULL;

-- One queue per service. Its status is the service's open/closed availability.
-- service_id has no foreign key yet: services are still kept in memory.
CREATE TABLE IF NOT EXISTS Queue (
    queue_id TEXT PRIMARY KEY NOT NULL CHECK (length(queue_id) = 36),
    service_id TEXT NOT NULL UNIQUE CHECK (length(service_id) BETWEEN 1 AND 100),
    status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
    created_at TEXT NOT NULL CHECK (datetime(created_at) IS NOT NULL)
) STRICT;

CREATE TABLE IF NOT EXISTS QueueEntry (
    entry_id TEXT PRIMARY KEY NOT NULL CHECK (length(entry_id) = 36),
    queue_id TEXT NOT NULL REFERENCES Queue(queue_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES UserCredentials(user_id) ON DELETE CASCADE,
    -- Increasing join counter: arrival order, even when two join times match.
    arrival INTEGER NOT NULL UNIQUE CHECK (arrival > 0),
    ticket TEXT NOT NULL CHECK (length(ticket) BETWEEN 3 AND 20),
    -- 1 is next in line. Only waiting entries have a position.
    position INTEGER CHECK (position IS NULL OR position > 0),
    joined_at TEXT NOT NULL CHECK (datetime(joined_at) IS NOT NULL),
    -- Existing API name: left = canceled.
    status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'served', 'left')),
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('normal', 'urgent')),
    finished_at TEXT CHECK (finished_at IS NULL OR datetime(finished_at) IS NOT NULL),
    -- Copied at join time so an entry keeps its name and duration if the service is deleted.
    service_name TEXT NOT NULL CHECK (length(service_name) BETWEEN 1 AND 100),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes BETWEEN 1 AND 480),
    CHECK ((status = 'waiting') = (position IS NOT NULL)),
    CHECK ((status = 'waiting') = (finished_at IS NULL))
) STRICT;

-- A user can wait in only one queue at a time.
CREATE UNIQUE INDEX IF NOT EXISTS QueueEntry_one_waiting_per_user ON QueueEntry(user_id) WHERE status = 'waiting';
CREATE INDEX IF NOT EXISTS QueueEntry_by_queue ON QueueEntry(queue_id, status);

-- Position updates shown on the patient's queue page, numbered per entry.
CREATE TABLE IF NOT EXISTS QueueEntryUpdate (
    entry_id TEXT NOT NULL REFERENCES QueueEntry(entry_id) ON DELETE CASCADE,
    update_id INTEGER NOT NULL CHECK (update_id > 0),
    kind TEXT NOT NULL CHECK (kind IN ('joined', 'moved', 'delayed', 'almost-ready', 'served')),
    message TEXT NOT NULL CHECK (length(message) BETWEEN 1 AND 200),
    at TEXT NOT NULL CHECK (datetime(at) IS NOT NULL),
    PRIMARY KEY (entry_id, update_id)
) STRICT;

-- Activity belongs to both a queue entry and its account. The composite key
-- prevents storing another student's user_id on an entry's notification/history.
CREATE UNIQUE INDEX IF NOT EXISTS QueueEntry_identity_user ON QueueEntry(entry_id, user_id);

CREATE TABLE IF NOT EXISTS Notification (
    notification_id TEXT PRIMARY KEY NOT NULL CHECK (length(notification_id) = 36),
    user_id TEXT NOT NULL REFERENCES UserCredentials(user_id) ON DELETE CASCADE,
    entry_id TEXT NOT NULL,
    event_key TEXT NOT NULL CHECK (length(event_key) BETWEEN 1 AND 100),
    ticket TEXT NOT NULL CHECK (length(ticket) BETWEEN 3 AND 20),
    service_id TEXT NOT NULL CHECK (length(service_id) BETWEEN 1 AND 100),
    service_name TEXT NOT NULL CHECK (length(trim(service_name)) BETWEEN 1 AND 100),
    kind TEXT NOT NULL CHECK (kind IN ('joined', 'moved', 'delayed', 'almost-ready', 'served', 'left')),
    category TEXT NOT NULL CHECK (category IN ('queue', 'status')),
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
    message TEXT NOT NULL CHECK (length(trim(message)) BETWEEN 1 AND 400),
    at TEXT NOT NULL CHECK (datetime(at) IS NOT NULL),
    -- "sent" means available in the in-app feed; no email or SMS is sent.
    status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'viewed')),
    UNIQUE (entry_id, event_key),
    FOREIGN KEY (entry_id, user_id) REFERENCES QueueEntry(entry_id, user_id) ON DELETE CASCADE,
    CHECK ((category = 'queue') = (kind IN ('moved', 'delayed')))
) STRICT;
CREATE INDEX IF NOT EXISTS Notification_by_user ON Notification(user_id, at DESC);

CREATE TABLE IF NOT EXISTS History (
    entry_id TEXT PRIMARY KEY NOT NULL,
    user_id TEXT NOT NULL REFERENCES UserCredentials(user_id) ON DELETE CASCADE,
    ticket TEXT NOT NULL CHECK (length(ticket) BETWEEN 3 AND 20),
    service_id TEXT NOT NULL CHECK (length(service_id) BETWEEN 1 AND 100),
    service_name TEXT NOT NULL CHECK (length(trim(service_name)) BETWEEN 1 AND 100),
    joined_at TEXT NOT NULL CHECK (datetime(joined_at) IS NOT NULL),
    finished_at TEXT NOT NULL CHECK (datetime(finished_at) IS NOT NULL),
    outcome TEXT NOT NULL CHECK (outcome IN ('served', 'left')),
    waited_minutes INTEGER NOT NULL CHECK (waited_minutes >= 0),
    FOREIGN KEY (entry_id, user_id) REFERENCES QueueEntry(entry_id, user_id) ON DELETE CASCADE
) STRICT;
CREATE INDEX IF NOT EXISTS History_by_user ON History(user_id, finished_at DESC);
