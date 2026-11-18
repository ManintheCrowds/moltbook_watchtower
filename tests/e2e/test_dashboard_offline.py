# PURPOSE: Generated dashboard renders charts, networks, word clouds and heatmap over file://
#   with every non-file:// request aborted (vendored libs, no CDN).
import pytest
from playwright.sync_api import Page

from tests.dashboard_fixture import generate_dashboard, seed_sample_db

CHART_CANVAS_IDS = [
    "chartSeverityPie",
    "chartPostsOverTime",
    "chartFindingsOverTime",
    "chartBehaviorOverTime",
    "chartFindingsByRule",
    "chartCommentsPerPost",
]
WORDCLOUD_CANVAS_IDS = ["wordcloudMolts", "wordcloudSubmolts"]
NETWORK_IDS = ["networkGraph", "networkCommentGraph"]


def check_offline_render(page: Page) -> dict:
    """Evaluate render state of libraries, charts, networks, word clouds and heatmap."""
    return page.evaluate(
        """([chartIds, cloudIds, netIds]) => {
  const painted = (c) => {
    if (!c || !c.width || !c.height) return false;
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    for (let i = 3; i < d.length; i += 4) if (d[i] !== 0) return true;
    return false;
  };
  return {
    libs: {Chart: typeof Chart, vis: typeof vis, WordCloud: typeof WordCloud},
    charts: Object.fromEntries(chartIds.map(id => [id, !!(window.Chart && Chart.getChart(id))])),
    chartsPainted: Object.fromEntries(chartIds.map(id => [id, painted(document.getElementById(id))])),
    wordclouds: Object.fromEntries(cloudIds.map(id => [id, painted(document.getElementById(id))])),
    networks: Object.fromEntries(netIds.map(id => {
      const el = document.getElementById(id);
      return [id, !!(el && el.querySelector('canvas'))];
    })),
    heatmapCells: document.querySelectorAll('td[title][style*="background-color"]').length,
    heatmapNonZero: Array.from(document.querySelectorAll('td[title][style*="background-color"]'))
      .filter(td => td.textContent.trim() !== '0').length,
  };
}""",
        [CHART_CANVAS_IDS, WORDCLOUD_CANVAS_IDS, NETWORK_IDS],
    )


@pytest.mark.e2e
def test_dashboard_renders_offline_from_file_url(page: Page, tmp_path) -> None:
    seed_sample_db(tmp_path / "watchtower.db")
    out = generate_dashboard(tmp_path)

    blocked: list[str] = []
    console_errors: list[str] = []

    def _route(route) -> None:
        if route.request.url.startswith("file://"):
            route.continue_()
        else:
            blocked.append(route.request.url)
            route.abort()

    page.route("**/*", _route)
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))
    page.goto(out.as_uri(), wait_until="load")
    page.wait_for_timeout(1500)  # chart animations / word cloud layout

    result = check_offline_render(page)
    assert result["libs"] == {"Chart": "function", "vis": "object", "WordCloud": "function"}, result
    assert all(result["charts"].values()), result
    assert all(result["chartsPainted"].values()), result
    assert all(result["wordclouds"].values()), result
    assert all(result["networks"].values()), result
    assert result["heatmapCells"] > 0 and result["heatmapNonZero"] > 0, result
    assert blocked == [], f"dashboard attempted network requests: {blocked}"
    assert console_errors == [], console_errors
