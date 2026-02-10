#!/usr/bin/env python3
# PURPOSE: Report grounded vs rhetoric finding counts per agent, per submolt, and over time.
# DEPENDENCIES: config, src.storage
# MODIFICATION NOTES: Read-only; writes to exports/grounded_ratios.md (or DATA_DIR/exports/).

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.storage import get_connection


def main() -> None:
    settings = get_settings(require_api_key=False)
    exports = settings.db_path.parent / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    out_path = exports / "grounded_ratios.md"

    conn = get_connection(settings.db_path)
    cur = conn.cursor()

    # Per-agent: distinct items (post_id, comment_id) with grounded vs ling/drift
    cur.execute(
        """
        WITH expanded AS (
            SELECT f.post_id, f.comment_id, f.rule_id,
                COALESCE(c.agent_name, p.agent_name) AS agent_name
            FROM findings f
            LEFT JOIN posts p ON f.post_id = p.id
            LEFT JOIN comments c ON f.comment_id = c.id AND c.post_id = f.post_id
        ),
        items AS (
            SELECT post_id, comment_id, agent_name,
                MAX(CASE WHEN rule_id LIKE 'grounded_%%' THEN 1 ELSE 0 END) AS has_grounded,
                MAX(CASE WHEN rule_id LIKE 'ling_%%' OR rule_id LIKE 'drift_%%' THEN 1 ELSE 0 END) AS has_rhetoric
            FROM expanded
            GROUP BY post_id, comment_id, agent_name
        )
        SELECT agent_name,
            SUM(has_grounded) AS grounded_items,
            SUM(has_rhetoric) AS rhetoric_items
        FROM items
        WHERE agent_name IS NOT NULL AND agent_name != ''
        GROUP BY agent_name
        HAVING grounded_items > 0 OR rhetoric_items > 0
        ORDER BY (grounded_items + rhetoric_items) DESC
        LIMIT 30
        """
    )
    agent_rows = cur.fetchall()

    # Per-submolt
    cur.execute(
        """
        WITH expanded AS (
            SELECT f.post_id, f.comment_id, f.rule_id, p.submolt
            FROM findings f
            LEFT JOIN posts p ON f.post_id = p.id
        ),
        items AS (
            SELECT post_id, comment_id, submolt,
                MAX(CASE WHEN rule_id LIKE 'grounded_%%' THEN 1 ELSE 0 END) AS has_grounded,
                MAX(CASE WHEN rule_id LIKE 'ling_%%' OR rule_id LIKE 'drift_%%' THEN 1 ELSE 0 END) AS has_rhetoric
            FROM expanded
            GROUP BY post_id, comment_id, submolt
        )
        SELECT submolt,
            SUM(has_grounded) AS grounded_items,
            SUM(has_rhetoric) AS rhetoric_items
        FROM items
        WHERE submolt IS NOT NULL AND submolt != ''
        GROUP BY submolt
        HAVING grounded_items > 0 OR rhetoric_items > 0
        ORDER BY (grounded_items + rhetoric_items) DESC
        LIMIT 20
        """
    )
    submolt_rows = cur.fetchall()

    # Over time: findings count by date and prefix
    cur.execute(
        """
        SELECT date(created_at) AS d,
            CASE
                WHEN rule_id LIKE 'grounded_%%' THEN 'grounded'
                WHEN rule_id LIKE 'ling_%%' OR rule_id LIKE 'drift_%%' THEN 'rhetoric'
                ELSE 'other'
            END AS prefix,
            COUNT(*) AS cnt
        FROM findings
        WHERE created_at IS NOT NULL
        GROUP BY d, prefix
        ORDER BY d, prefix
        """
    )
    trend_rows = cur.fetchall()
    conn.close()

    # Build markdown
    lines = [
        "# Grounded vs rhetoric ratios",
        "",
        "Distinct items (post or comment) with at least one grounded_* vs ling_*/drift_* finding.",
        "",
        "## Per agent (top 30 by activity)",
        "",
        "| agent_name | grounded_items | rhetoric_items | total |",
        "|------------|----------------|----------------|-------|",
    ]
    for r in agent_rows:
        agent, g, rh = r[0], r[1], r[2]
        total = g + rh
        lines.append(f"| {agent} | {g} | {rh} | {total} |")
    if not agent_rows:
        lines.append("| (none) | 0 | 0 | 0 |")
    lines.extend(["", "## Per submolt (top 20)", "", "| submolt | grounded_items | rhetoric_items | total |", "|---------|----------------|----------------|-------|"])
    for r in submolt_rows:
        submolt, g, rh = r[0], r[1], r[2]
        total = g + rh
        lines.append(f"| {submolt} | {g} | {rh} | {total} |")
    if not submolt_rows:
        lines.append("| (none) | 0 | 0 | 0 |")
    lines.extend(["", "## Trend (findings per day by prefix)", "", "| date | prefix | count |", "|------|--------|-------|"])
    for r in trend_rows:
        d, prefix, cnt = r[0], r[1], r[2]
        lines.append(f"| {d} | {prefix} | {cnt} |")
    if not trend_rows:
        lines.append("| (none) | - | 0 |")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
    sys.exit(0)
