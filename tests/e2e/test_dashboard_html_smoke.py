# PURPOSE: MW-1 — smoke test for generated static dashboard HTML (informational read-only surface).
# MW-3 guards: SR tables, aria-describedby targets, network regions (regression without full a11y tooling).
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

# Canvas / word-cloud elements with aria-describedby → single id (must exist in DOM).
_CHART_CANVAS_ADB_IDS = [
    "chartSeverityPie",
    "chartPostsOverTime",
    "chartFindingsOverTime",
    "chartBehaviorOverTime",
    "chartFindingsByRule",
    "chartCommentsPerPost",
    "wordcloudMolts",
    "wordcloudSubmolts",
]

# Elements that must expose aria-describedby with resolvable id token(s).
_ARIA_DESCRIBEDBY_PARENT_IDS = _CHART_CANVAS_ADB_IDS + [
    "networkGraph",
    "networkCommentGraph",
]

# SR-only tables: 8 titled charts/clouds + 2 networks × 2 tables (nodes + edges).
_EXPECTED_SR_CHART_TABLE_COUNT = 8 + 2 * 2


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


def _assert_aria_describedby_targets_resolved(page: Page) -> None:
    """Every aria-describedby token must match an existing element id (MW-3)."""
    missing = page.evaluate(
        """(allIds) => {
  const missing = [];
  for (const cid of allIds) {
    const el = document.getElementById(cid);
    if (!el) { missing.push(cid + ':missing'); continue; }
    const adb = el.getAttribute('aria-describedby');
    if (!adb) { missing.push(cid + ':no-aria-describedby'); continue; }
    for (const id of adb.trim().split(/\\s+/)) {
      if (id && !document.getElementById(id)) missing.push(cid + '->' + id);
    }
  }
  return missing;
}""",
        _ARIA_DESCRIBEDBY_PARENT_IDS,
    )
    assert missing == [], f"aria-describedby broken or missing ids: {missing}"


@pytest.mark.e2e
def test_dashboard_html_smoke(page: Page, dashboard_html_url: str) -> None:
    """Generated dashboard loads without console errors; key sections, MW-3 SR/a11y hooks, and title present."""
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
    expect(page.get_by_text("network_edges.csv", exact=False)).to_be_visible()
    expect(page.get_by_text("TELEMETRY_AND_NETWORK_VIZ.md", exact=False)).to_be_visible()

    # MW-3: SR-only tables (charts, word clouds, network node/edge tables).
    expect(page.locator("main table.sr-chart-table")).to_have_count(_EXPECTED_SR_CHART_TABLE_COUNT)

    # Network landmark regions (agent–submolt + comment thread).
    expect(page.locator("main .network-region[role='region']")).to_have_count(2)
    expect(page.locator("#heading-network-agent-submolt")).to_be_attached()
    expect(page.locator("#heading-comment-threads")).to_be_attached()

    _assert_aria_describedby_targets_resolved(page)

    # MW-6: embedded print stylesheet (regression guard for @media print)
    has_print_css = page.evaluate(
        """() => Array.from(document.querySelectorAll("style")).some(
      (s) => s.textContent && s.textContent.includes("@media print")
    )"""
    )
    assert has_print_css, "expected @media print rules in embedded stylesheet"

    assert not console_errors, f"browser console errors: {console_errors}"
