-- Assignment 4: credentials and profiles. Enable foreign keys for manual use too.
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
