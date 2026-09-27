-- Times are fractional days since the Monday on or before the first request.
CREATE TABLE requests (
    unique_key     TEXT PRIMARY KEY,
    complaint_type TEXT NOT NULL,
    descriptor     TEXT,
    address        TEXT,
    created_d      REAL NOT NULL,
    closed_d       REAL,              -- NULL if open, or closed at an unknown time
    is_closed      INTEGER NOT NULL,
    is_duplicate   INTEGER NOT NULL
);

CREATE TABLE weeks (week INTEGER PRIMARY KEY);

CREATE TABLE targets (
    complaint_type TEXT PRIMARY KEY,
    target_days    REAL NOT NULL
);

-- The requests the analysis uses: no duplicates, and no closed requests whose
-- close time we couldn't recover (they would distort both trends and ages).
CREATE VIEW clean AS
SELECT * FROM requests
WHERE is_duplicate = 0
  AND NOT (is_closed = 1 AND closed_d IS NULL);
