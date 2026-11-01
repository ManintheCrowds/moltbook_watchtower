# PURPOSE: Integration test — fixture DB, run report_summary, generate_dashboard_html, export_network; assert output files and content.
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.analyzers.base import Finding
from src.storage import StorageWriter, get_connection, init_db


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _build_fixture_db(db_path: Path) -> None:
    init_db(db_path)
    writer = StorageWriter(db_path)
    writer.write_posts_response([
        {"id": "p1", "title": "T1", "content": "C1", "author": {"name": "a1"}, "submolt": "s1", "created_at": "2025-01-01T12:00:00Z"},
        {"id": "p2", "title": "T2", "author": {"name": "a2"}, "submolt": "s1"},
    ])
    writer.write_post_comments("p1", [{"id": "c1", "content": "comment", "author": {"name": "a2"}}])
    writer.insert_findings([
        Finding(post_id="p1", comment_id=None, rule_id="r1", severity="high", redacted_snippet="***"),
    ])


def test_pipeline_report_dashboard_export(tmp_path) -> None:
    db_path = tmp_path / "watchtower.db"
    _build_fixture_db(db_path)
    env = {**os.environ, "DATA_DIR": str(tmp_path)}
    repo = _repo_root()
    script_dir = repo / "scripts"

    subprocess.run(
        [sys.executable, str(script_dir / "report_summary.py")],
        env=env,
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    assert (tmp_path / "exports" / "summary_report.md").exists()
    content = (tmp_path / "exports" / "summary_report.md").read_text(encoding="utf-8")
    assert "Moltbook Watchtower" in content
    assert "Total posts" in content

    subprocess.run(
        [sys.executable, str(script_dir / "generate_dashboard_html.py")],
        env=env,
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    assert (tmp_path / "exports" / "dashboard.html").exists()
    html = (tmp_path / "exports" / "dashboard.html").read_text(encoding="utf-8")
    assert "Moltbook Watchtower" in html
    assert "last_generated" in html

    subprocess.run(
        [sys.executable, str(script_dir / "export_network.py")],
        env=env,
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    assert (tmp_path / "exports" / "network_edges.csv").exists()
    csv_lines = (tmp_path / "exports" / "network_edges.csv").read_text(encoding="utf-8").strip().split("\n")
    assert len(csv_lines) >= 1
    assert "source,target,weight,edge_type" in csv_lines[0]


def test_dashboard_heatmap_with_post_dated_today(tmp_path) -> None:
    """Regression: posts within the 14-day heatmap window must not crash dashboard JSON serialization."""
    from datetime import datetime, timezone

    db_path = tmp_path / "watchtower.db"
    init_db(db_path)
    now = datetime.now(timezone.utc)
    today_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    writer = StorageWriter(db_path)
    writer.write_posts_response([
        {"id": "p_today", "title": "Today", "content": "fresh post", "author": {"name": "agent_today"}, "submolt": "s1", "created_at": today_iso},
    ])
    env = {**os.environ, "DATA_DIR": str(tmp_path)}
    repo = _repo_root()

    result = subprocess.run(
        [sys.executable, str(repo / "scripts" / "generate_dashboard_html.py")],
        env=env,
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "exports" / "dashboard.html").read_text(encoding="utf-8")
    assert "agent_today" in html
    assert f"agent_today|{now.date().isoformat()}" in html


def test_run_analyzers_on_fresh_data_dir(tmp_path) -> None:
    """Regression: run_analyzers.py must create the schema when no DB exists yet (fresh clone)."""
    env = {**os.environ, "DATA_DIR": str(tmp_path / "data"), "LOG_DIR": str(tmp_path / "logs")}
    env.pop("MOLTBOOK_API_KEY", None)
    repo = _repo_root()
    result = subprocess.run(
        [sys.executable, str(repo / "scripts" / "run_analyzers.py")],
        env=env,
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "data" / "watchtower.db").exists()
