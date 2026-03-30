# PURPOSE: MW-1 — smoke test for generated static dashboard HTML (informational read-only surface).
import functools
import os
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from src.storage import init_db

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def dashboard_html_url(tmp_path, monkeypatch):
    """Fixture DB under DATA_DIR → generate_dashboard_html → serve tmp_path over HTTP."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    db_path = tmp_path / "watchtower.db"
    init_db(db_path)

    env = {**os.environ, "DATA_DIR": str(tmp_path)}
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_dashboard_html.py")],
        cwd=str(REPO_ROOT),
        check=True,
        env=env,
    )

    out = tmp_path / "exports" / "dashboard.html"
    assert out.is_file(), f"expected generator to write {out}"

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(tmp_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/exports/dashboard.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_dashboard_html_smoke(page: Page, dashboard_html_url: str) -> None:
    """Generated dashboard loads without console errors; key sections and title present."""
    console_errors: list[str] = []

    def _on_console(msg) -> None:
        if msg.type == "error":
            console_errors.append(msg.text)

    page.on("console", _on_console)
    page.goto(dashboard_html_url, wait_until="domcontentloaded")

    expect(page).to_have_title("Moltbook Watchtower")
    expect(page.locator("main#main-content")).to_be_visible()
    expect(page.get_by_role("heading", name="Moltbook Watchtower", level=1)).to_be_visible()
    expect(page.get_by_text("Total posts:", exact=False)).to_be_visible()
    expect(page.get_by_role("heading", name="Findings by rule", exact=True, level=2)).to_be_visible()
    expect(page.get_by_text("export_network.py", exact=False)).to_be_visible()
    expect(page.get_by_text("TELEMETRY_AND_NETWORK_VIZ.md", exact=False)).to_be_visible()

    assert not console_errors, f"browser console errors: {console_errors}"
