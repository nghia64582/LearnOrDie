CREATE TABLE extraunary (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    name TEXT NOT NULL,
    score INTEGER NOT NULL
    -- index for filter by time
);
CREATE INDEX idx_date ON extraunary (created_at)