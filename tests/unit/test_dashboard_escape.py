# PURPOSE: SEC-1 — dashboard HTML escapes DB-sourced strings (stored XSS mitigation).
import os
import subprocess
import sys
from pathlib import Path

from src.storage import StorageWriter, get_connection, init_db

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
XSS_AGENT = '<script>alert(1)</script>'
XSS_SUBMOLT = '"><img src=x onerror=alert(1)>'
XSS_SNIPPET = "<b>evil</b>"


def test_dashboard_escapes_db_sourced_table_cells(tmp_path, monkeypatch) -> None:
    """Malicious post/agent/submolt/finding strings must be HTML-escaped in dashboard output."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db_path = tmp_path / "watchtower.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    writer.write_posts_response(
        [
            {
                "id": "p-xss",
                "title": "t",
                "content": "c",
                "author": {"name": XSS_AGENT},
                "submolt": XSS_SUBMOLT,
                "created_at": "2025-06-01T12:00:00Z",
            }
        ]
    )
    writer.insert_finding("p-xss", None, "rule_<test>", "high", XSS_SNIPPET)

    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_dashboard_html.py")],
        cwd=str(REPO_ROOT),
        env={**os.environ, "DATA_DIR": str(tmp_path)},
        check=True,
    )
    html_path = tmp_path / "exports" / "dashboard.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")

    # Table cells (SEC-1) must be escaped in visible HTML tables.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in html
    assert "&lt;b&gt;evil&lt;/b&gt;" in html
    assert "rule_&lt;test&gt;" in html
    assert "<script>alert(1)</script>" not in html
    # Recent findings table tbody must not contain raw snippet HTML.
    marker = "Recent findings (last 50)"
    idx = html.find(marker)
    assert idx != -1
    tbody_start = html.find("<tbody>", idx)
    tbody_end = html.find("</tbody>", tbody_start)
    findings_tbody = html[tbody_start:tbody_end]
    assert "<b>evil</b>" not in findings_tbody
