#!/usr/bin/env python3
# PURPOSE: Daily/weekly summary report — total posts, flagged counts; no raw secrets.
# DEPENDENCIES: config, src.storage
# MODIFICATION NOTES: Output to exports/; optional DAILY_REPORT_DIR for date-named file in repo.

import os
import sys
from datetime import date
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.storage import get_connection


def _report_date() -> str:
    """Report date as YYYY-MM-DD from env REPORT_DATE or today."""
    raw = os.getenv("REPORT_DATE", "").strip()
    if raw:
        return raw
    return date.today().isoformat()


def main() -> None:
    settings = get_settings(require_api_key=False)
    conn = get_connection(settings.db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM posts")
        total_posts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM comments")
        total_comments = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM findings")
        total_findings = cur.fetchone()[0]
        cur.execute(
            "SELECT rule_id, severity, COUNT(*) FROM findings GROUP BY rule_id, severity ORDER BY COUNT(*) DESC"
        )
        findings_by_rule = cur.fetchall()
    finally:
        conn.close()

    content = (
        "# Moltbook Watchtower — Summary Report\n\n"
        f"- Total posts: {total_posts}\n"
        f"- Total comments: {total_comments}\n"
        f"- Total findings: {total_findings}\n\n"
        "## Findings by rule\n\n"
        "| rule_id | severity | count |\n| --- | --- | --- |\n"
    )
    for rule_id, severity, count in findings_by_rule:
        content += f"| {rule_id} | {severity} | {count} |\n"

    exports = settings.db_path.parent / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    path = exports / "summary_report.md"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")

    daily_dir = getattr(settings, "daily_report_dir", None)
    if daily_dir:
        daily_dir.mkdir(parents=True, exist_ok=True)
        daily_path = daily_dir / f"{_report_date()}.md"
        daily_path.write_text(content, encoding="utf-8")
        print(f"Wrote {daily_path}")


if __name__ == "__main__":
    main()
