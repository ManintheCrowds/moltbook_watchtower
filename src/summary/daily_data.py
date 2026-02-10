# PURPOSE: Query DB for counts, findings, and post highlights for a given date; no raw secrets.
# DEPENDENCIES: src.storage.get_connection
# MODIFICATION NOTES: Used by prompt_builder; content truncated for token budget.

from pathlib import Path
from typing import Any

# Caps for prompt size
FINDINGS_CAP = 20
HIGHLIGHTS_CONTENT_CHARS = 200
HIGHLIGHTS_CAP = 30


def get_daily_data(db_path: Path, report_date: str) -> dict[str, Any]:
    """Return counts (total + on-date), findings (capped), and post highlights for report_date.
    report_date is YYYY-MM-DD. No raw secrets; redacted_snippet only for findings."""
    from src.storage import get_connection

    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        # Counts: total and new on date D
        cur.execute("SELECT COUNT(*) FROM posts")
        total_posts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM comments")
        total_comments = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM findings")
        total_findings = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM posts WHERE date(created_at) = ?",
            (report_date,),
        )
        posts_on_date = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM comments WHERE date(created_at) = ?",
            (report_date,),
        )
        comments_on_date = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM findings WHERE date(created_at) = ?",
            (report_date,),
        )
        findings_on_date = cur.fetchone()[0]

        # Findings for date (or latest N): rule_id, severity, redacted_snippet
        cur.execute(
            """
            SELECT rule_id, severity, redacted_snippet
            FROM findings
            WHERE date(created_at) = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (report_date, FINDINGS_CAP),
        )
        findings_rows = cur.fetchall()
        if not findings_rows:
            cur.execute(
                """
                SELECT rule_id, severity, redacted_snippet
                FROM findings
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (FINDINGS_CAP,),
            )
            findings_rows = cur.fetchall()
        findings = [
            {
                "rule_id": r[0],
                "severity": r[1],
                "redacted_snippet": (r[2] or "").strip(),
            }
            for r in findings_rows
        ]

        # Highlights: posts with date(created_at) = D; title, truncated content, agent_name, submolt
        cur.execute(
            """
            SELECT title, content, agent_name, submolt, created_at
            FROM posts
            WHERE date(created_at) = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (report_date, HIGHLIGHTS_CAP),
        )
        rows = cur.fetchall()
        highlights = []
        for r in rows:
            title = (r[0] or "").strip()
            content = (r[1] or "").strip()
            if len(content) > HIGHLIGHTS_CONTENT_CHARS:
                content = content[:HIGHLIGHTS_CONTENT_CHARS] + "..."
            highlights.append({
                "title": title,
                "content_snippet": content,
                "agent_name": (r[2] or "").strip(),
                "submolt": (r[3] or "").strip(),
                "created_at": (r[4] or "").strip(),
            })
        return {
            "report_date": report_date,
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_findings": total_findings,
            "posts_on_date": posts_on_date,
            "comments_on_date": comments_on_date,
            "findings_on_date": findings_on_date,
            "findings": findings,
            "highlights": highlights,
        }
    finally:
        conn.close()
