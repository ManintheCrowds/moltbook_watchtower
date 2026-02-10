# PURPOSE: SQLite schema and connection for Watchtower; DB lives in data/ (gitignored).
# DEPENDENCIES: sqlite3 stdlib, pathlib
# MODIFICATION NOTES: Idempotent upsert by external ID.
"""SQLite schema and connection for Watchtower; data/ is gitignored."""

import sqlite3
from pathlib import Path
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    name TEXT PRIMARY KEY,
    description TEXT,
    karma INTEGER,
    follower_count INTEGER,
    following_count INTEGER,
    is_claimed INTEGER,
    is_active INTEGER,
    created_at TEXT,
    last_active TEXT,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submolts (
    name TEXT PRIMARY KEY,
    display_name TEXT,
    description TEXT,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    agent_name TEXT,
    submolt TEXT,
    title TEXT,
    content TEXT,
    url TEXT,
    upvotes INTEGER,
    downvotes INTEGER,
    created_at TEXT,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_name) REFERENCES agents(name)
);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    agent_name TEXT,
    content TEXT,
    parent_id TEXT,
    upvotes INTEGER,
    created_at TEXT,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT,
    comment_id TEXT,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    redacted_snippet TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_agent ON posts(agent_name);
CREATE INDEX IF NOT EXISTS idx_posts_submolt ON posts(submolt);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_findings_post ON findings(post_id);
CREATE INDEX IF NOT EXISTS idx_findings_rule ON findings(rule_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_findings_dedup ON findings(post_id, comment_id, rule_id);

CREATE TABLE IF NOT EXISTS behavior_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_type TEXT NOT NULL,
    window_start TEXT,
    window_end TEXT,
    key_name TEXT,
    value_real REAL,
    value_int INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_behavior_metric_type ON behavior_metrics(metric_type);
"""


def init_db(db_path: Path) -> None:
    """Create data dir and DB; apply schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(_SCHEMA)


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Return an open connection (caller must close or use as context manager)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
