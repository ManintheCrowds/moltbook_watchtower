# PURPOSE: Aggregate by time/agent/submolt; flag anomalies (post burst, submolt spike).
# DEPENDENCIES: sqlite3, src.analyzers.base.Finding
# MODIFICATION NOTES: Persist metrics to behavior_metrics; anomalies as findings (no raw content).
# created_at in posts should be stored in ISO UTC so datetime('now') window comparison is correct.
"""Behavior anomaly detector (post burst, submolt spike)."""

import sqlite3
from typing import Iterator

from .base import Finding

# Thresholds
POSTS_PER_AGENT_IN_WINDOW = 10  # anomaly if agent posts this many in window
WINDOW_MINUTES = 5
SUBMOLT_GROWTH_POSTS = 50  # anomaly if submolt gains this many posts in window


class BehaviorAnalyzer:
    """Computes metrics and yields anomaly findings. Pass a single cursor; run() uses it for reads and conn for writes."""

    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def run(self) -> Iterator[Finding]:
        """Run behavior analysis; persist metrics; yield anomaly findings."""
        conn = getattr(self._cursor, "connection", None)
        cursor = self._cursor

        # Posts per agent in last N minutes
        cursor.execute(
            """
            SELECT agent_name, COUNT(*) AS cnt
            FROM posts
            WHERE created_at >= datetime('now', ?)
            AND agent_name IS NOT NULL
            GROUP BY agent_name
            HAVING cnt >= ?
            """,
            (f"-{WINDOW_MINUTES} minutes", POSTS_PER_AGENT_IN_WINDOW),
        )
        for row in cursor.fetchall():
            agent_name, cnt = row[0], row[1]
            if conn:
                conn.execute(
                    "INSERT INTO behavior_metrics (metric_type, key_name, value_int, created_at) VALUES (?, ?, ?, datetime('now'))",
                    ("posts_per_agent_window", agent_name or "", cnt),
                )
            yield Finding(
                post_id=None,
                comment_id=None,
                rule_id="behavior_post_burst",
                severity="medium",
                redacted_snippet=f"agent={agent_name} posts_in_window={cnt}",
            )

        # Submolt growth (posts in last window)
        cursor.execute(
            """
            SELECT submolt, COUNT(*) AS cnt
            FROM posts
            WHERE created_at >= datetime('now', ?)
            AND submolt IS NOT NULL
            GROUP BY submolt
            HAVING cnt >= ?
            """,
            (f"-{WINDOW_MINUTES} minutes", SUBMOLT_GROWTH_POSTS),
        )
        for row in cursor.fetchall():
            submolt, cnt = row[0], row[1]
            if conn:
                conn.execute(
                    "INSERT INTO behavior_metrics (metric_type, key_name, value_int, created_at) VALUES (?, ?, ?, datetime('now'))",
                    ("submolt_growth_window", submolt or "", cnt),
                )
            yield Finding(
                post_id=None,
                comment_id=None,
                rule_id="behavior_submolt_spike",
                severity="low",
                redacted_snippet=f"submolt={submolt} new_posts_in_window={cnt}",
            )

        if conn:
            conn.commit()
