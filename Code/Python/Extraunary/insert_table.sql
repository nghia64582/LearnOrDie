CREATE TABLE extraunary (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    name TEXT NOT NULL,
    score INTEGER NOT NULL,
    year INTEGER NOT NULL,
    -- index for filter by time
    CREATE INDEX idx_date ON extraunary (year, month, day)
);