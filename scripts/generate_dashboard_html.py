#!/usr/bin/env python3
# PURPOSE: Generate static HTML dashboard with tables and Chart.js graphs; no raw secrets.
# DEPENDENCIES: config, src.storage
# MODIFICATION NOTES: Embeds JSON in HTML for single-file portability; exports/dashboard.html (gitignored).

import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.storage import get_connection

# Stopwords for word clouds (common English + short); min word length 2
_STOPWORDS = frozenset(
    "the and for is to of in it you that he was on are with as his they at be this have from or one had by word but not what all were we when your can said there use each which she do how their if will up out many then them these so some her would make like into him time two more no go way could my than first been call who oil sit now find long down day did get come made may part".split()
)


def _tokenize_word_freq(texts: list[str], top_n: int = 80) -> list[list]:
    """Build [word, count] list for wordcloud2 from concatenated text; exclude stopwords."""
    combined = " ".join((t or "").lower() for t in texts)
    words = re.findall(r"[a-z]{2,}", combined)
    counts = Counter(w for w in words if w not in _STOPWORDS)
    return [[w, c] for w, c in counts.most_common(top_n)]


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
            "SELECT rule_id, severity, COUNT(*) FROM findings GROUP BY rule_id, severity ORDER BY COUNT(*) DESC LIMIT 20"
        )
        findings_by_rule = [{"rule_id": r[0], "severity": r[1], "count": r[2]} for r in cur.fetchall()]
        cur.execute(
            "SELECT post_id, comment_id, rule_id, severity, redacted_snippet, created_at FROM findings ORDER BY created_at DESC LIMIT 50"
        )
        recent_findings = [
            {"post_id": r[0], "comment_id": r[1], "rule_id": r[2], "severity": r[3], "redacted_snippet": r[4] or "", "created_at": r[5] or ""}
            for r in cur.fetchall()
        ]
        cur.execute(
            "SELECT submolt, COUNT(*) as c FROM posts WHERE submolt IS NOT NULL AND submolt != '' GROUP BY submolt ORDER BY c DESC LIMIT 10"
        )
        submolts_by_posts = [{"submolt": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT date(created_at) as d, COUNT(*) FROM posts WHERE created_at IS NOT NULL GROUP BY d ORDER BY d"
        )
        posts_per_day = [{"date": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT date(created_at) as d, COUNT(*) FROM findings GROUP BY d ORDER BY d"
        )
        findings_per_day = [{"date": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT post_id, COUNT(*) as c FROM comments GROUP BY post_id ORDER BY c DESC LIMIT 10"
        )
        comments_per_post = [{"post_id": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT agent_name, COUNT(*) as c FROM posts WHERE agent_name IS NOT NULL AND agent_name != '' GROUP BY agent_name ORDER BY c DESC LIMIT 20"
        )
        top_agents_by_posts = [{"agent_name": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT agent_name, COUNT(*) as c FROM comments WHERE agent_name IS NOT NULL AND agent_name != '' GROUP BY agent_name ORDER BY c DESC LIMIT 20"
        )
        top_agents_by_comments = [{"agent_name": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT metric_type, key_name, value_int, created_at FROM behavior_metrics ORDER BY created_at DESC LIMIT 50"
        )
        recent_behavior_metrics = [
            {"metric_type": r[0], "key_name": r[1], "value_int": r[2], "created_at": r[3] or ""}
            for r in cur.fetchall()
        ]
        cur.execute(
            """
            SELECT agent_name, submolt, COUNT(*) AS cnt
            FROM posts
            WHERE agent_name IS NOT NULL AND agent_name != '' AND submolt IS NOT NULL AND submolt != ''
            GROUP BY agent_name, submolt
            ORDER BY cnt DESC
            """
        )
        agent_submolt_edges = [(r[0], r[1], r[2]) for r in cur.fetchall()]
        cur.execute("SELECT severity, COUNT(*) FROM findings GROUP BY severity ORDER BY severity")
        findings_by_severity = [{"severity": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            """
            SELECT date(created_at) AS d, metric_type, COUNT(*) AS cnt
            FROM behavior_metrics
            WHERE created_at IS NOT NULL
            GROUP BY date(created_at), metric_type
            ORDER BY d
            """
        )
        behavior_per_day = [{"date": r[0], "metric_type": r[1], "count": r[2]} for r in cur.fetchall()]

        # Grounded vs rhetoric: per agent (distinct items with grounded / ling|drift findings)
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
            SELECT agent_name, SUM(has_grounded) AS grounded_items, SUM(has_rhetoric) AS rhetoric_items
            FROM items
            WHERE agent_name IS NOT NULL AND agent_name != ''
            GROUP BY agent_name
            HAVING grounded_items > 0 OR rhetoric_items > 0
            ORDER BY (grounded_items + rhetoric_items) DESC
            LIMIT 20
            """
        )
        agent_grounded_ratios = [
            {"agent_name": r[0], "grounded_items": r[1], "rhetoric_items": r[2]}
            for r in cur.fetchall()
        ]
        # Per submolt
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
            SELECT submolt, SUM(has_grounded) AS grounded_items, SUM(has_rhetoric) AS rhetoric_items
            FROM items
            WHERE submolt IS NOT NULL AND submolt != ''
            GROUP BY submolt
            HAVING grounded_items > 0 OR rhetoric_items > 0
            ORDER BY (grounded_items + rhetoric_items) DESC
            LIMIT 15
            """
        )
        submolt_grounded_ratios = [
            {"submolt": r[0], "grounded_items": r[1], "rhetoric_items": r[2]}
            for r in cur.fetchall()
        ]
        # Trend: findings per day by prefix (pivot to grounded / rhetoric columns)
        cur.execute(
            """
            SELECT date(created_at) AS d,
                CASE WHEN rule_id LIKE 'grounded_%%' THEN 'grounded'
                     WHEN rule_id LIKE 'ling_%%' OR rule_id LIKE 'drift_%%' THEN 'rhetoric'
                     ELSE 'other' END AS prefix,
                COUNT(*) AS cnt
            FROM findings
            WHERE created_at IS NOT NULL
            GROUP BY d, prefix
            ORDER BY d, prefix
            """
        )
        trend_raw = cur.fetchall()
        by_date = {}
        for d, prefix, cnt in trend_raw:
            if d not in by_date:
                by_date[d] = {"date": d, "grounded": 0, "rhetoric": 0}
            if prefix == "grounded":
                by_date[d]["grounded"] = cnt
            elif prefix == "rhetoric":
                by_date[d]["rhetoric"] = cnt
        grounded_trend = sorted(by_date.values(), key=lambda x: x["date"])

        # Agent activity heatmap: top N agents x last 14 days
        cur.execute(
            """
            SELECT agent_name, date(created_at) AS d, COUNT(*) AS cnt
            FROM posts
            WHERE agent_name IS NOT NULL AND agent_name != ''
              AND created_at IS NOT NULL
              AND date(created_at) >= date('now', '-14 days')
            GROUP BY agent_name, date(created_at)
            ORDER BY agent_name, d
            """
        )
        agent_day_counts = [(r[0], r[1], r[2]) for r in cur.fetchall()]
        # Comment-thread sample: one post with up to 50 comments (comment→post, comment→parent_id)
        cur.execute(
            """
            SELECT c.id, c.post_id, c.parent_id
            FROM comments c
            ORDER BY c.post_id, c.created_at
            LIMIT 5000
            """
        )
        comment_rows = cur.fetchall()
        # Word clouds: molts = post title+content + comment content; submolts = names + descriptions
        cur.execute(
            "SELECT title, content FROM posts WHERE (title IS NOT NULL OR content IS NOT NULL) ORDER BY created_at DESC LIMIT 500"
        )
        post_texts = [(r[0] or "", r[1] or "") for r in cur.fetchall()]
        cur.execute("SELECT content FROM comments WHERE content IS NOT NULL AND content != '' LIMIT 2000")
        comment_texts = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT name, display_name, description FROM submolts WHERE (name IS NOT NULL OR display_name IS NOT NULL OR description IS NOT NULL)"
        )
        submolt_rows = cur.fetchall()
        cur.execute(
            "SELECT submolt, COUNT(*) FROM posts WHERE submolt IS NOT NULL AND submolt != '' GROUP BY submolt"
        )
        submolt_post_counts = {r[0]: r[1] for r in cur.fetchall()}
    finally:
        conn.close()

    # Build agent heatmap: top 15 agents by total posts in last 14 days, columns = dates
    dates_14 = [(datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat() for i in range(13, -1, -1)]
    agent_counts_by_day = {}
    agent_totals = {}
    for agent, d, cnt in agent_day_counts:
        d_str = d if isinstance(d, str) else (d.isoformat() if d else "")
        agent_counts_by_day[(agent, d_str)] = cnt
        agent_totals[agent] = agent_totals.get(agent, 0) + cnt
    top_agents_heatmap = sorted(agent_totals.keys(), key=lambda a: agent_totals[a], reverse=True)[:15]
    heatmap_max = max(agent_counts_by_day.values(), default=1)

    # Comment-thread nodes and edges (one post + up to 50 comments)
    post_comment_map = {}
    for cid, pid, parent_id in comment_rows:
        post_comment_map.setdefault(pid, []).append((cid, parent_id))
    sample_post_id = None
    sample_comments = []
    for pid, comments in post_comment_map.items():
        if len(comments) >= 1:
            sample_post_id = pid
            sample_comments = comments[:50]
            break
    network_comment_nodes = []
    network_comment_edges = []
    sample_comment_ids = {cid for cid, _ in sample_comments}
    if sample_post_id:
        network_comment_nodes.append({"id": f"post_{sample_post_id}", "label": sample_post_id[:12] + "…", "type": "post"})
        for cid, parent_id in sample_comments:
            network_comment_nodes.append({"id": f"comment_{cid}", "label": cid[:8] + "…", "type": "comment"})
            network_comment_edges.append({"from": f"comment_{cid}", "to": f"post_{sample_post_id}", "value": 1})
            if parent_id and parent_id in sample_comment_ids:
                network_comment_edges.append({"from": f"comment_{cid}", "to": f"comment_{parent_id}", "value": 1})

    # Word clouds: molts from post title+content and comment content; submolts from names (weighted by post count) + descriptions
    molts_texts = [f"{t} {c}" for t, c in post_texts] + list(comment_texts)
    word_freq_molts = _tokenize_word_freq(molts_texts, top_n=80)
    submolt_texts = []
    for name, display_name, description in submolt_rows:
        count = submolt_post_counts.get(name, 1)
        # Repeat submolt name by post count so it appears larger in cloud; add display_name and description
        submolt_texts.extend([name] * count)
        if display_name:
            submolt_texts.append(display_name)
        if description:
            submolt_texts.append(description)
    word_freq_submolts = _tokenize_word_freq(submolt_texts, top_n=50)

    node_ids = set()
    for agent, submolt, _ in agent_submolt_edges:
        node_ids.add(("agent", agent))
        node_ids.add(("submolt", submolt))
    network_nodes = [
        {"id": f"{ntype}_{nid}", "label": nid, "type": ntype}
        for ntype, nid in sorted(node_ids, key=lambda x: (x[0], x[1]))
    ]
    network_edges = [
        {"from": f"agent_{agent}", "to": f"submolt_{submolt}", "value": cnt}
        for agent, submolt, cnt in agent_submolt_edges
    ]

    last_generated = datetime.now(timezone.utc).isoformat()
    data = {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_findings": total_findings,
        "findings_by_rule": findings_by_rule,
        "recent_findings": recent_findings,
        "submolts_by_posts": submolts_by_posts,
        "posts_per_day": posts_per_day,
        "findings_per_day": findings_per_day,
        "comments_per_post": comments_per_post,
        "top_agents_by_posts": top_agents_by_posts,
        "top_agents_by_comments": top_agents_by_comments,
        "recent_behavior_metrics": recent_behavior_metrics,
        "last_generated": last_generated,
        "network_nodes": network_nodes,
        "network_edges": network_edges,
        "findings_by_severity": findings_by_severity,
        "behavior_per_day": behavior_per_day,
        "agent_heatmap": {
            "dates": dates_14,
            "agents": top_agents_heatmap,
            "cells": agent_counts_by_day,
            "max": heatmap_max,
        },
        "network_comment_nodes": network_comment_nodes,
        "network_comment_edges": network_comment_edges,
        "word_freq_molts": word_freq_molts,
        "word_freq_submolts": word_freq_submolts,
        "agent_grounded_ratios": agent_grounded_ratios,
        "submolt_grounded_ratios": submolt_grounded_ratios,
        "grounded_trend": grounded_trend,
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")

    # Agent heatmap table HTML (rows = agents, cols = dates, bg color by count)
    def _heatmap_cell(agent: str, d: str) -> str:
        cnt = agent_counts_by_day.get((agent, d), 0)
        pct = (cnt / heatmap_max * 100) if heatmap_max else 0
        bg = f"rgba(75, 192, 192, {0.2 + 0.8 * pct / 100:.2f})"
        return f'<td style="background-color:{bg}" title="{agent} {d}: {cnt}">{cnt}</td>'
    heatmap_header = "".join(f"<th>{d[5:]}</th>" for d in dates_14)
    heatmap_rows_html = ""
    for agent in top_agents_heatmap:
        cells = "".join(_heatmap_cell(agent, d) for d in dates_14)
        heatmap_rows_html += f"<tr><td>{agent[:20]}</td>{cells}</tr>"
    if not top_agents_heatmap:
        heatmap_rows_html = "<tr><td colspan='15'>No data for this period</td></tr>"

    rows_html = "".join(
        f"<tr><td>{r['rule_id']}</td><td>{r['severity']}</td><td>{r['count']}</td></tr>"
        for r in findings_by_rule
    ) or "<tr><td colspan='3'>No data for this period</td></tr>"
    recent_rows = "".join(
        f"<tr><td>{r['post_id']}</td><td>{r['comment_id'] or ''}</td><td>{r['rule_id']}</td><td>{r['severity']}</td><td>{r['redacted_snippet'][:80]!s}</td><td>{r['created_at']}</td></tr>"
        for r in recent_findings
    ) or "<tr><td colspan='6'>No data for this period</td></tr>"
    submolt_rows = "".join(
        f"<tr><td>{r['submolt']}</td><td>{r['count']}</td></tr>" for r in submolts_by_posts
    ) or "<tr><td colspan='2'>No data for this period</td></tr>"
    top_agents_posts_rows = "".join(
        f"<tr><td>{r['agent_name']}</td><td>{r['count']}</td></tr>" for r in top_agents_by_posts
    ) or "<tr><td colspan='2'>No data for this period</td></tr>"
    top_agents_comments_rows = "".join(
        f"<tr><td>{r['agent_name']}</td><td>{r['count']}</td></tr>" for r in top_agents_by_comments
    ) or "<tr><td colspan='2'>No data for this period</td></tr>"
    behavior_rows = "".join(
        f"<tr><td>{r['metric_type']}</td><td>{r['key_name']}</td><td>{r['value_int']}</td><td>{r['created_at']}</td></tr>"
        for r in recent_behavior_metrics
    ) or "<tr><td colspan='4'>No data for this period</td></tr>"
    agent_grounded_rows = "".join(
        f"<tr><td>{r['agent_name']}</td><td>{r['grounded_items']}</td><td>{r['rhetoric_items']}</td><td>{r['grounded_items'] + r['rhetoric_items']}</td></tr>"
        for r in agent_grounded_ratios
    ) or "<tr><td colspan='4'>No data</td></tr>"
    submolt_grounded_rows = "".join(
        f"<tr><td>{r['submolt']}</td><td>{r['grounded_items']}</td><td>{r['rhetoric_items']}</td><td>{r['grounded_items'] + r['rhetoric_items']}</td></tr>"
        for r in submolt_grounded_ratios
    ) or "<tr><td colspan='4'>No data</td></tr>"
    grounded_trend_rows = "".join(
        f"<tr><td>{r['date']}</td><td>{r['grounded']}</td><td>{r['rhetoric']}</td></tr>"
        for r in grounded_trend
    ) or "<tr><td colspan='3'>No data</td></tr>"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Moltbook Watchtower</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/wordcloud2.js/1.0.2/wordcloud2.min.js"></script>
</head>
<body>
<h1>Moltbook Watchtower</h1>
<p>Total posts: <strong>{total_posts}</strong> | Total comments: <strong>{total_comments}</strong> | Total findings: <strong>{total_findings}</strong></p>
<p><small>Last generated: {last_generated}</small></p>

<h2>Findings by rule</h2>
<table border="1">
<thead><tr><th>rule_id</th><th>severity</th><th>count</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>

<h2>Recent findings (last 50)</h2>
<table border="1">
<thead><tr><th>post_id</th><th>comment_id</th><th>rule_id</th><th>severity</th><th>redacted_snippet</th><th>created_at</th></tr></thead>
<tbody>{recent_rows}</tbody>
</table>

<h2>Top submolts by post count</h2>
<table border="1">
<thead><tr><th>submolt</th><th>count</th></tr></thead>
<tbody>{submolt_rows}</tbody>
</table>

<h2>Top agents by posts</h2>
<table border="1">
<thead><tr><th>agent_name</th><th>count</th></tr></thead>
<tbody>{top_agents_posts_rows}</tbody>
</table>

<h2>Top agents by comments</h2>
<table border="1">
<thead><tr><th>agent_name</th><th>count</th></tr></thead>
<tbody>{top_agents_comments_rows}</tbody>
</table>

<h2>Recent behavior metrics</h2>
<table border="1">
<thead><tr><th>metric_type</th><th>key_name</th><th>value_int</th><th>created_at</th></tr></thead>
<tbody>{behavior_rows}</tbody>
</table>

<h2>Grounded vs rhetoric (distinct items)</h2>
<p>Items = post or comment with at least one grounded_* or ling_*/drift_* finding.</p>
<h3>Per agent (top 20)</h3>
<table border="1">
<thead><tr><th>agent_name</th><th>grounded_items</th><th>rhetoric_items</th><th>total</th></tr></thead>
<tbody>{agent_grounded_rows}</tbody>
</table>
<h3>Per submolt (top 15)</h3>
<table border="1">
<thead><tr><th>submolt</th><th>grounded_items</th><th>rhetoric_items</th><th>total</th></tr></thead>
<tbody>{submolt_grounded_rows}</tbody>
</table>
<h3>Trend (findings per day)</h3>
<table border="1">
<thead><tr><th>date</th><th>grounded</th><th>rhetoric</th></tr></thead>
<tbody>{grounded_trend_rows}</tbody>
</table>

<h2>Findings by severity (pie)</h2>
<canvas id="chartSeverityPie" width="300" height="200"></canvas>
<p id="emptySeverityPie" class="empty-state" style="display:none">No data for this period</p>

<h2>Posts over time (daily)</h2>
<canvas id="chartPostsOverTime" width="400" height="150"></canvas>
<p id="emptyPostsOverTime" class="empty-state" style="display:none">No data for this period</p>

<h2>Findings over time (daily)</h2>
<canvas id="chartFindingsOverTime" width="400" height="150"></canvas>
<p id="emptyFindingsOverTime" class="empty-state" style="display:none">No data for this period</p>

<h2>Behavior metrics over time (daily)</h2>
<canvas id="chartBehaviorOverTime" width="400" height="150"></canvas>
<p id="emptyBehaviorOverTime" class="empty-state" style="display:none">No data for this period</p>

<h2>Findings by rule (bar)</h2>
<canvas id="chartFindingsByRule" width="400" height="200"></canvas>
<p id="emptyFindingsByRule" class="empty-state" style="display:none">No data for this period</p>

<h2>Comments per post (top 10)</h2>
<canvas id="chartCommentsPerPost" width="400" height="200"></canvas>
<p id="emptyCommentsPerPost" class="empty-state" style="display:none">No data for this period</p>

<h2>Agent activity heatmap (last 14 days)</h2>
<table border="1"><thead><tr><th>Agent</th>{heatmap_header}</tr></thead><tbody>{heatmap_rows_html}</tbody></table>

<h2>Network: Agent–Submolt</h2>
<div id="networkGraph" style="width: 100%; max-width: 800px; height: 400px;"></div>
<p id="emptyNetwork" class="empty-state" style="display:none">No data for this period</p>

<h2>Comment threads (sample)</h2>
<div id="networkCommentGraph" style="width: 100%; max-width: 800px; height: 400px;"></div>
<p id="emptyNetworkComment" class="empty-state" style="display:none">No data for this period</p>

<h2>Word cloud: Molts (posts &amp; comments)</h2>
<canvas id="wordcloudMolts" width="700" height="350"></canvas>
<p id="emptyWordcloudMolts" class="empty-state" style="display:none">No text data for this period</p>

<h2>Word cloud: Submolts (names &amp; descriptions)</h2>
<canvas id="wordcloudSubmolts" width="700" height="300"></canvas>
<p id="emptyWordcloudSubmolts" class="empty-state" style="display:none">No submolt data for this period</p>

<script type="application/json" id="dashboardData">{data_json}</script>
<script>
(function() {{
  var raw = document.getElementById('dashboardData').textContent;
  var data = JSON.parse(raw);

  function dailyChart(canvasId, label, dates, counts) {{
    var ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: dates,
        datasets: [{{ label: label, data: counts, borderColor: 'rgb(75, 192, 192)', fill: false }}]
      }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
  }}

  function showEmpty(canvasId, emptyId, showEmptyState) {{
    var c = document.getElementById(canvasId);
    var e = document.getElementById(emptyId);
    if (c) c.style.display = showEmptyState ? 'none' : 'block';
    if (e) e.style.display = showEmptyState ? 'block' : 'none';
  }}

  if (data.posts_per_day && data.posts_per_day.length) {{
    dailyChart('chartPostsOverTime', 'Posts', data.posts_per_day.map(function(x) {{ return x.date; }}), data.posts_per_day.map(function(x) {{ return x.count; }}));
    showEmpty('chartPostsOverTime', 'emptyPostsOverTime', false);
  }} else {{ showEmpty('chartPostsOverTime', 'emptyPostsOverTime', true); }}
  if (data.findings_per_day && data.findings_per_day.length) {{
    dailyChart('chartFindingsOverTime', 'Findings', data.findings_per_day.map(function(x) {{ return x.date; }}), data.findings_per_day.map(function(x) {{ return x.count; }}));
    showEmpty('chartFindingsOverTime', 'emptyFindingsOverTime', false);
  }} else {{ showEmpty('chartFindingsOverTime', 'emptyFindingsOverTime', true); }}

  if (data.findings_by_severity && data.findings_by_severity.length) {{
    var ctx = document.getElementById('chartSeverityPie').getContext('2d');
    new Chart(ctx, {{
      type: 'pie',
      data: {{
        labels: data.findings_by_severity.map(function(x) {{ return x.severity; }}),
        datasets: [{{ data: data.findings_by_severity.map(function(x) {{ return x.count; }}), backgroundColor: ['#97C2FC', '#FB7E81', '#7AE7C7', '#FFB84D'] }}]
      }},
      options: {{ responsive: true }}
    }});
    showEmpty('chartSeverityPie', 'emptySeverityPie', false);
  }} else {{ showEmpty('chartSeverityPie', 'emptySeverityPie', true); }}

  if (data.behavior_per_day && data.behavior_per_day.length) {{
    var byType = {{}};
    var allDatesSet = {{}};
    data.behavior_per_day.forEach(function(r) {{
      if (!byType[r.metric_type]) byType[r.metric_type] = {{}};
      byType[r.metric_type][r.date] = r.count;
      allDatesSet[r.date] = true;
    }});
    var allDates = Object.keys(allDatesSet).sort();
    var colors = ['rgb(75, 192, 192)', 'rgb(255, 99, 132)', 'rgb(255, 206, 86)'];
    var datasets = Object.keys(byType).map(function(t, i) {{
      return {{ label: t, data: allDates.map(function(d) {{ return byType[t][d] || 0; }}), borderColor: colors[i % colors.length], fill: false }};
    }});
    var ctx = document.getElementById('chartBehaviorOverTime').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{ labels: allDates, datasets: datasets }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
    showEmpty('chartBehaviorOverTime', 'emptyBehaviorOverTime', false);
  }} else {{ showEmpty('chartBehaviorOverTime', 'emptyBehaviorOverTime', true); }}

  if (data.findings_by_rule && data.findings_by_rule.length) {{
    var ctx = document.getElementById('chartFindingsByRule').getContext('2d');
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: data.findings_by_rule.map(function(x) {{ return x.rule_id; }}),
        datasets: [{{ label: 'Count', data: data.findings_by_rule.map(function(x) {{ return x.count; }}), backgroundColor: 'rgba(54, 162, 235, 0.5)' }}]
      }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
    showEmpty('chartFindingsByRule', 'emptyFindingsByRule', false);
  }} else {{ showEmpty('chartFindingsByRule', 'emptyFindingsByRule', true); }}

  if (data.comments_per_post && data.comments_per_post.length) {{
    var ctx = document.getElementById('chartCommentsPerPost').getContext('2d');
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: data.comments_per_post.map(function(x) {{ return x.post_id; }}),
        datasets: [{{ label: 'Comments', data: data.comments_per_post.map(function(x) {{ return x.count; }}), backgroundColor: 'rgba(255, 99, 132, 0.5)' }}]
      }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
    showEmpty('chartCommentsPerPost', 'emptyCommentsPerPost', false);
  }} else {{ showEmpty('chartCommentsPerPost', 'emptyCommentsPerPost', true); }}

  if (typeof vis !== 'undefined' && data.network_nodes && data.network_nodes.length && data.network_edges && data.network_edges.length) {{
    var container = document.getElementById('networkGraph');
    var nodes = new vis.DataSet(data.network_nodes.map(function(n) {{
      return {{ id: n.id, label: n.label, group: n.type, title: n.type + ': ' + n.label }};
    }}));
    var edges = new vis.DataSet(data.network_edges.map(function(e) {{
      return {{ from: e.from, to: e.to, value: e.value, title: e.value + ' posts' }};
    }}));
    var opts = {{
      nodes: {{ shape: 'dot', font: {{ size: 12 }} }},
      edges: {{ width: 0.5 }},
      physics: {{ enabled: true }},
      groups: {{ agent: {{ color: '#97C2FC' }}, submolt: {{ color: '#FB7E81' }} }}
    }};
    new vis.Network(container, {{ nodes: nodes, edges: edges }}, opts);
    showEmpty('networkGraph', 'emptyNetwork', false);
  }} else {{ showEmpty('networkGraph', 'emptyNetwork', true); }}

  if (typeof vis !== 'undefined' && data.network_comment_nodes && data.network_comment_nodes.length && data.network_comment_edges && data.network_comment_edges.length) {{
    var containerComment = document.getElementById('networkCommentGraph');
    var nodesComment = new vis.DataSet(data.network_comment_nodes.map(function(n) {{
      return {{ id: n.id, label: n.label, group: n.type, title: n.type + ': ' + n.label }};
    }}));
    var edgesComment = new vis.DataSet(data.network_comment_edges.map(function(e) {{
      return {{ from: e.from, to: e.to, value: e.value || 1 }};
    }}));
    var optsComment = {{
      nodes: {{ shape: 'dot', font: {{ size: 10 }} }},
      edges: {{ width: 0.5 }},
      physics: {{ enabled: true }},
      groups: {{ post: {{ color: '#7AE7C7' }}, comment: {{ color: '#FFB84D' }} }}
    }};
    new vis.Network(containerComment, {{ nodes: nodesComment, edges: edgesComment }}, optsComment);
    var emptyComment = document.getElementById('emptyNetworkComment');
    if (emptyComment) emptyComment.style.display = 'none';
  }} else {{
    var emptyComment = document.getElementById('emptyNetworkComment');
    if (emptyComment) emptyComment.style.display = 'block';
  }}

  if (typeof WordCloud !== 'undefined') {{
    var canvasMolts = document.getElementById('wordcloudMolts');
    var emptyMolts = document.getElementById('emptyWordcloudMolts');
    if (data.word_freq_molts && data.word_freq_molts.length) {{
      if (canvasMolts) canvasMolts.style.display = 'block';
      if (emptyMolts) emptyMolts.style.display = 'none';
      WordCloud(canvasMolts, {{
        list: data.word_freq_molts,
        gridSize: 8,
        weightFactor: 2,
        fontFamily: 'sans-serif',
        color: 'random-light'
      }});
    }} else {{
      if (canvasMolts) canvasMolts.style.display = 'none';
      if (emptyMolts) emptyMolts.style.display = 'block';
    }}
    var canvasSub = document.getElementById('wordcloudSubmolts');
    var emptySub = document.getElementById('emptyWordcloudSubmolts');
    if (data.word_freq_submolts && data.word_freq_submolts.length) {{
      if (canvasSub) canvasSub.style.display = 'block';
      if (emptySub) emptySub.style.display = 'none';
      WordCloud(canvasSub, {{
        list: data.word_freq_submolts,
        gridSize: 8,
        weightFactor: 2,
        fontFamily: 'sans-serif',
        color: 'random-dark'
      }});
    }} else {{
      if (canvasSub) canvasSub.style.display = 'none';
      if (emptySub) emptySub.style.display = 'block';
    }}
  }}
}})();
</script>
<footer style="margin-top:2em; font-size:0.9em; color:#666;">
<p>Export network data: run <code>python scripts/export_network.py</code>; see <code>docs/TELEMETRY_AND_NETWORK_VIZ.md</code> for Gephi, NodeXL, Cytoscape, etc.</p>
</footer>
</body>
</html>
"""
    exports = settings.db_path.parent / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    path = exports / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
