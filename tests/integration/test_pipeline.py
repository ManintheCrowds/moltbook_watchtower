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
