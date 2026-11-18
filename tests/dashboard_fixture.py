# PURPOSE: Shared fixture data for dashboard tests (offline render / vendored libs).
# DEPENDENCIES: src.storage
# MODIFICATION NOTES: Synthetic data only; populates every chart, network, word cloud and heatmap.
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.storage import StorageWriter, get_connection, init_db

REPO_ROOT = Path(__file__).resolve().parent.parent


def seed_sample_db(db_path: Path) -> None:
    """Create a DB with posts, comments, submolts, findings and behavior metrics over recent days."""
    init_db(db_path)
    writer = StorageWriter(db_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    agents = ["agent_alpha", "agent_beta", "agent_gamma", "agent_delta"]
    submolts = ["general", "security", "philosophy"]
    writer.write_submolts_response(
        [
            {"name": "general", "description": "general discussion about agents and tools"},
            {"name": "security", "description": "security research prompt injection defenses"},
            {"name": "philosophy", "description": "philosophy of agents consciousness memory"},
        ]
    )
    posts = []
    for i in range(18):
        ts = (now - timedelta(days=i % 7, hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        posts.append(
            {
                "id": f"p{i}",
                "title": f"Sample post {i}",
                "content": "agents discuss memory tools security grounded evidence rhetoric watchtower",
                "author": {"name": agents[i % len(agents)]},
                "submolt": submolts[i % len(submolts)],
                "created_at": ts,
            }
        )
    writer.write_posts_response(posts)
    for i in range(6):
        writer.write_post_comments(
            f"p{i}",
            [
                {
                    "id": f"c{i}_{j}",
                    "content": "reply about memory and tools",
                    "author": {"name": agents[(i + j + 1) % len(agents)]},
                    "created_at": posts[i]["created_at"],
                }
                for j in range(1 + i % 3)
            ],
        )
    rules = [("grounded_citation", "low"), ("ling_hype", "medium"), ("drift_topic", "high"), ("leak_api_key", "high")]
    for i in range(10):
        rule, sev = rules[i % len(rules)]
        writer.insert_finding(f"p{i}", None, rule, sev, "[REDACTED]")
    conn = get_connection(db_path)
    try:
        for i in range(8):
            d = (now - timedelta(days=i % 5)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO findings (post_id, comment_id, rule_id, severity, redacted_snippet, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"p{10 + i}", None, rules[i % len(rules)][0], rules[i % len(rules)][1], "[REDACTED]", d),
            )
            conn.execute(
                "INSERT INTO behavior_metrics (metric_type, key_name, value_int, created_at) VALUES (?, ?, ?, ?)",
                ("post_burst" if i % 2 else "reply_rate", agents[i % len(agents)], i + 1, d),
            )
        conn.commit()
    finally:
        conn.close()


def generate_dashboard(data_dir: Path) -> Path:
    """Run the dashboard generator against DATA_DIR and return exports/dashboard.html."""
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_dashboard_html.py")],
        cwd=str(REPO_ROOT),
        env={**os.environ, "DATA_DIR": str(data_dir)},
        check=True,
    )
    out = data_dir / "exports" / "dashboard.html"
    assert out.is_file(), f"expected generator to write {out}"
    return out
