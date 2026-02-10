# PURPOSE: Idempotent upsert of Moltbook API responses into SQLite.
# DEPENDENCIES: src.storage.db
# MODIFICATION NOTES: Normalizes API response shapes; no raw content in logs.
"""Idempotent upsert of API responses; no raw content in logs."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional  # noqa: F401 used for insert_finding

from .db import get_connection, init_db


def _ts(val: Any) -> Optional[str]:
    if val is None:
        return None
    return str(val)


def _int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


class StorageWriter:
    """Writes API responses to SQLite; idempotent upsert by external ID."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        init_db(db_path)

    def _upsert_agent(self, conn: sqlite3.Connection, row: dict[str, Any]) -> None:
        name = _ts(row.get("name") or row.get("agent_name"))
        if not name:
            return
        conn.execute(
            """
            INSERT INTO agents (name, description, karma, follower_count, following_count,
                is_claimed, is_active, created_at, last_active, raw_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                description=excluded.description,
                karma=excluded.karma,
                follower_count=excluded.follower_count,
                following_count=excluded.following_count,
                is_claimed=excluded.is_claimed,
                is_active=excluded.is_active,
                created_at=excluded.created_at,
                last_active=excluded.last_active,
                raw_json=excluded.raw_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                name,
                _ts(row.get("description")),
                _int(row.get("karma")),
                _int(row.get("follower_count")),
                _int(row.get("following_count")),
                1 if row.get("is_claimed") else 0,
                1 if row.get("is_active") else 0,
                _ts(row.get("created_at")),
                _ts(row.get("last_active")),
                json.dumps(row) if row else None,
            ),
        )

    def _upsert_submolt(self, conn: sqlite3.Connection, row: dict[str, Any]) -> None:
        name = _ts(row.get("name"))
        if not name:
            return
        conn.execute(
            """
            INSERT INTO submolts (name, display_name, description, raw_json, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                display_name=excluded.display_name,
                description=excluded.description,
                raw_json=excluded.raw_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                name,
                _ts(row.get("display_name")),
                _ts(row.get("description")),
                json.dumps(row) if row else None,
            ),
        )

    def _upsert_post(self, conn: sqlite3.Connection, row: dict[str, Any]) -> None:
        post_id = _ts(row.get("id"))
        if not post_id:
            return
        author = row.get("author") or {}
        agent_name = _ts(author.get("name")) if isinstance(author, dict) else None
        submolt_obj = row.get("submolt")
        if isinstance(submolt_obj, dict):
            submolt = _ts(submolt_obj.get("name"))
        else:
            submolt = _ts(submolt_obj) or _ts(row.get("submolt"))
        conn.execute(
            """
            INSERT INTO posts (id, agent_name, submolt, title, content, url, upvotes, downvotes, created_at, raw_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                agent_name=excluded.agent_name,
                submolt=excluded.submolt,
                title=excluded.title,
                content=excluded.content,
                url=excluded.url,
                upvotes=excluded.upvotes,
                downvotes=excluded.downvotes,
                created_at=excluded.created_at,
                raw_json=excluded.raw_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                post_id,
                agent_name,
                submolt,
                _ts(row.get("title")),
                _ts(row.get("content")),
                _ts(row.get("url")),
                _int(row.get("upvotes")),
                _int(row.get("downvotes")),
                _ts(row.get("created_at")),
                json.dumps(row) if row else None,
            ),
        )
        if agent_name:
            self._upsert_agent(conn, {"name": agent_name, **author} if isinstance(author, dict) else {"name": agent_name})

    def _upsert_comment(self, conn: sqlite3.Connection, post_id: str, row: dict[str, Any]) -> None:
        comment_id = _ts(row.get("id"))
        if not comment_id:
            return
        author = row.get("author") or {}
        agent_name = _ts(author.get("name")) if isinstance(author, dict) else None
        conn.execute(
            """
            INSERT INTO comments (id, post_id, agent_name, content, parent_id, upvotes, created_at, raw_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                agent_name=excluded.agent_name,
                content=excluded.content,
                parent_id=excluded.parent_id,
                upvotes=excluded.upvotes,
                created_at=excluded.created_at,
                raw_json=excluded.raw_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                comment_id,
                post_id,
                agent_name,
                _ts(row.get("content")),
                _ts(row.get("parent_id")),
                _int(row.get("upvotes")),
                _ts(row.get("created_at")),
                json.dumps(row) if row else None,
            ),
        )
        if agent_name:
            self._upsert_agent(conn, {"name": agent_name, **author} if isinstance(author, dict) else {"name": agent_name})

    def write_posts_response(self, body: Any) -> int:
        """Parse API posts/feed response and upsert posts. Returns count written. Does not log content."""
        if not body or not isinstance(body, (list, dict)):
            return 0
        posts = body if isinstance(body, list) else (body.get("posts") or body.get("data") or body.get("results") or [])
        if not isinstance(posts, list):
            return 0
        conn = get_connection(self._db_path)
        try:
            n = 0
            for p in posts:
                if isinstance(p, dict):
                    self._upsert_post(conn, p)
                    n += 1
            conn.commit()
            return n
        finally:
            conn.close()

    def write_submolts_response(self, body: Any) -> int:
        """Parse API submolts response and upsert. Returns count written."""
        if not body or not isinstance(body, (list, dict)):
            return 0
        items = body if isinstance(body, list) else (body.get("submolts") or body.get("data") or [])
        if not isinstance(items, list):
            return 0
        conn = get_connection(self._db_path)
        try:
            n = 0
            for s in items:
                if isinstance(s, dict) and s.get("name"):
                    self._upsert_submolt(conn, s)
                    n += 1
            conn.commit()
            return n
        finally:
            conn.close()

    def write_post_comments(self, post_id: str, body: Any) -> int:
        """Parse comments response for a post; upsert comments. Returns count written."""
        if not body or not isinstance(body, (list, dict)):
            return 0
        items = body if isinstance(body, list) else (body.get("comments") or body.get("data") or [])
        if not isinstance(items, list):
            return 0
        conn = get_connection(self._db_path)
        try:
            n = 0
            for c in items:
                if isinstance(c, dict):
                    self._upsert_comment(conn, post_id, c)
                    n += 1
            conn.commit()
            return n
        finally:
            conn.close()

    def insert_finding(
        self,
        post_id: Optional[str],
        comment_id: Optional[str],
        rule_id: str,
        severity: str,
        redacted_snippet: Optional[str] = None,
    ) -> None:
        """Insert one analyzer finding (no raw secrets). Duplicates by (post_id, comment_id, rule_id) are ignored."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO findings (post_id, comment_id, rule_id, severity, redacted_snippet) VALUES (?, ?, ?, ?, ?)",
                (post_id, comment_id, rule_id, severity, redacted_snippet),
            )
            conn.commit()
        finally:
            conn.close()

    def insert_findings(self, findings: list) -> None:
        """Insert multiple findings in one connection; INSERT OR IGNORE for deduplication by (post_id, comment_id, rule_id)."""
        if not findings:
            return
        conn = get_connection(self._db_path)
        try:
            for f in findings:
                conn.execute(
                    "INSERT OR IGNORE INTO findings (post_id, comment_id, rule_id, severity, redacted_snippet) VALUES (?, ?, ?, ?, ?)",
                    (f.post_id, f.comment_id, f.rule_id, f.severity, f.redacted_snippet),
                )
            conn.commit()
        finally:
            conn.close()
