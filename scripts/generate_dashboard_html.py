#!/usr/bin/env python3
# PURPOSE: Generate static HTML dashboard with tables and Chart.js graphs; no raw secrets.
# DEPENDENCIES: config, src.storage
# MODIFICATION NOTES: Embeds JSON in HTML for single-file portability; exports/dashboard.html (gitignored).

import html as html_lib
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


def _captioned_table(caption: str, thead_tr: str, tbody_html: str) -> str:
    """Table with screen-reader-only caption (mirrors section heading)."""
    return (
        f'<table class="data-table" border="0"><caption class="visually-hidden">{html_lib.escape(caption)}</caption>'
        f"<thead>{thead_tr}</thead><tbody>{tbody_html}</tbody></table>"
    )


def _tokenize_word_freq(texts: list[str], top_n: int = 80) -> list[list]:
    """Build [word, count] list for wordcloud2 from concatenated text; exclude stopwords."""
    combined = " ".join((t or "").lower() for t in texts)
    words = re.findall(r"[a-z]{2,}", combined)
    counts = Counter(w for w in words if w not in _STOPWORDS)
    return [[w, c] for w, c in counts.most_common(top_n)]


_SR_MAX_BEHAVIOR_ROWS = 300


def _sr_chart_table(table_id: str, caption: str, thead_tr: str, tbody_html: str) -> str:
    """Off-screen data table for screen readers; id matches canvas aria-describedby."""
    return (
        f'<table id="{table_id}" class="sr-chart-table data-table" border="0">'
        f"<caption>{html_lib.escape(caption)}</caption>"
        f"<thead>{thead_tr}</thead><tbody>{tbody_html}</tbody></table>"
    )


def _sr_network_block(
    block_id: str,
    intro: str,
    nodes: list[dict],
    edges: list[dict],
) -> str:
    """Nodes and edges tables for SR; block id is network aria-describedby target."""
    if not nodes and not edges:
        tbody_n = "<tr><td colspan=\"3\">No data for this period</td></tr>"
        tbody_e = "<tr><td colspan=\"3\">No data for this period</td></tr>"
    else:
        tbody_n = "".join(
            "<tr>"
            f"<td>{html_lib.escape(str(n.get('id', '')))}</td>"
            f"<td>{html_lib.escape(str(n.get('label', '')))}</td>"
            f"<td>{html_lib.escape(str(n.get('type', '')))}</td>"
            "</tr>"
            for n in nodes
        ) or "<tr><td colspan=\"3\">No nodes</td></tr>"
        tbody_e = "".join(
            "<tr>"
            f"<td>{html_lib.escape(str(e.get('from', '')))}</td>"
            f"<td>{html_lib.escape(str(e.get('to', '')))}</td>"
            f"<td>{html_lib.escape(str(e.get('value', '')))}</td>"
            "</tr>"
            for e in edges
        ) or "<tr><td colspan=\"3\">No edges</td></tr>"
    return (
        f'<div id="{block_id}" class="sr-only-chart-block">'
        f'<p class="visually-hidden">{html_lib.escape(intro)}</p>'
        '<table class="sr-chart-table data-table" border="0">'
        "<caption>Network nodes</caption>"
        "<thead><tr><th>id</th><th>label</th><th>type</th></tr></thead>"
        f"<tbody>{tbody_n}</tbody></table>"
        '<table class="sr-chart-table data-table" border="0">'
        "<caption>Network edges</caption>"
        "<thead><tr><th>from</th><th>to</th><th>value</th></tr></thead>"
        f"<tbody>{tbody_e}</tbody></table>"
        "</div>"
    )


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

    # MW-3: SR-only tables for aria-describedby (same data as charts; complements canvas role="img")
    sr_severity = _sr_chart_table(
        "desc-chartSeverityPie",
        "Findings by severity (same data as the pie chart)",
        "<tr><th>Severity</th><th>Count</th></tr>",
        (
            "".join(
                f"<tr><td>{html_lib.escape(str(r['severity']))}</td><td>{r['count']}</td></tr>"
                for r in findings_by_severity
            )
            or "<tr><td colspan=\"2\">No data for this period</td></tr>"
        ),
    )

    sr_posts_ot = _sr_chart_table(
        "desc-chartPostsOverTime",
        "Posts per day (same data as the line chart)",
        "<tr><th>Date</th><th>Posts</th></tr>",
        (
            "".join(
                f"<tr><td>{html_lib.escape(str(r['date']))}</td><td>{r['count']}</td></tr>" for r in posts_per_day
            )
            or "<tr><td colspan=\"2\">No data for this period</td></tr>"
        ),
    )

    sr_findings_ot = _sr_chart_table(
        "desc-chartFindingsOverTime",
        "Findings per day (same data as the line chart)",
        "<tr><th>Date</th><th>Findings</th></tr>",
        (
            "".join(
                f"<tr><td>{html_lib.escape(str(r['date']))}</td><td>{r['count']}</td></tr>"
                for r in findings_per_day
            )
            or "<tr><td colspan=\"2\">No data for this period</td></tr>"
        ),
    )

    _beh = behavior_per_day[:_SR_MAX_BEHAVIOR_ROWS]
    _beh_trunc = len(behavior_per_day) > _SR_MAX_BEHAVIOR_ROWS
    _beh_cap = (
        f"Behavior metrics by day and type (same data as the multi-line chart; "
        f"showing first {_SR_MAX_BEHAVIOR_ROWS} rows"
        + ("; more rows omitted." if _beh_trunc else ".")
    )
    sr_behavior_ot = _sr_chart_table(
        "desc-chartBehaviorOverTime",
        _beh_cap,
        "<tr><th>Date</th><th>Metric type</th><th>Count</th></tr>",
        (
            "".join(
                "<tr>"
                f"<td>{html_lib.escape(str(r['date']))}</td>"
                f"<td>{html_lib.escape(str(r['metric_type']))}</td>"
                f"<td>{r['count']}</td>"
                "</tr>"
                for r in _beh
            )
            or "<tr><td colspan=\"3\">No data for this period</td></tr>"
        ),
    )

    sr_findings_rule = _sr_chart_table(
        "desc-chartFindingsByRule",
        "Findings by rule (same data as the bar chart)",
        "<tr><th>rule_id</th><th>severity</th><th>count</th></tr>",
        (
            "".join(
                "<tr>"
                f"<td>{html_lib.escape(str(r['rule_id']))}</td>"
                f"<td>{html_lib.escape(str(r['severity']))}</td>"
                f"<td>{r['count']}</td>"
                "</tr>"
                for r in findings_by_rule
            )
            or "<tr><td colspan=\"3\">No data for this period</td></tr>"
        ),
    )

    sr_comments_pp = _sr_chart_table(
        "desc-chartCommentsPerPost",
        "Comments per post, top sample (same data as the bar chart)",
        "<tr><th>post_id</th><th>comments</th></tr>",
        (
            "".join(
                f"<tr><td>{html_lib.escape(str(r['post_id']))}</td><td>{r['count']}</td></tr>"
                for r in comments_per_post
            )
            or "<tr><td colspan=\"2\">No data for this period</td></tr>"
        ),
    )

    sr_net = _sr_network_block(
        "desc-networkGraph",
        "Agent–submolt network: nodes are agents and submolts; edge values are post counts between pairs.",
        network_nodes,
        network_edges,
    )

    sr_net_c = _sr_network_block(
        "desc-networkCommentGraph",
        "Comment-thread sample network: post and comment nodes; edges show reply or post attachment.",
        network_comment_nodes,
        network_comment_edges,
    )

    sr_wc_m = _sr_chart_table(
        "desc-wordcloudMolts",
        "Word frequencies for molts (posts and comments), same weights as the word cloud",
        "<tr><th>Word</th><th>Weight</th></tr>",
        (
            "".join(f"<tr><td>{html_lib.escape(str(w))}</td><td>{c}</td></tr>" for w, c in word_freq_molts)
            or "<tr><td colspan=\"2\">No data for this period</td></tr>"
        ),
    )

    sr_wc_s = _sr_chart_table(
        "desc-wordcloudSubmolts",
        "Word frequencies for submolt names and descriptions, same weights as the word cloud",
        "<tr><th>Word</th><th>Weight</th></tr>",
        (
            "".join(f"<tr><td>{html_lib.escape(str(w))}</td><td>{c}</td></tr>" for w, c in word_freq_submolts)
            or "<tr><td colspan=\"2\">No data for this period</td></tr>"
        ),
    )

    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moltbook Watchtower</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600;700&amp;family=Source+Sans+3:ital,wght@0,400;0,600;1,400&amp;display=swap" rel="stylesheet">
<style>
:root {{
  --font-sans: "Source Sans 3", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --color-bg: #0d1117;
  --color-surface: #161b22;
  --color-border: #30363d;
  --color-text: #e6edf3;
  --color-muted: #8b949e;
  --color-accent: #58a6ff;
  --color-accent-warm: #c9a227;
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.75rem;
  --space-xl: 2.5rem;
  --radius-sm: 4px;
  --radius-md: 8px;
  --shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body.dashboard-body {{
  margin: 0;
  min-height: 100vh;
  font-family: var(--font-sans);
  font-size: 1rem;
  line-height: 1.55;
  color: var(--color-text);
  background: var(--color-bg);
  background-image: radial-gradient(ellipse 100% 60% at 50% -15%, rgba(88, 166, 255, 0.07), transparent 55%);
}}
main#main-content.dashboard-main {{
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-lg) var(--space-md) var(--space-xl);
  overflow-x: auto;
}}
@media (prefers-reduced-motion: no-preference) {{
  @keyframes dashboardReveal {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: none; }}
  }}
  main#main-content.dashboard-main {{
    animation: dashboardReveal 0.42s ease-out;
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
}}
h1 {{
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: clamp(1.45rem, 3.5vw, 1.95rem);
  letter-spacing: -0.03em;
  margin: 0 0 var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}}
h2 {{
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 1.08rem;
  margin: var(--space-xl) 0 var(--space-md);
  color: var(--color-accent-warm);
  letter-spacing: 0.03em;
}}
h3 {{
  font-size: 0.98rem;
  font-weight: 600;
  margin: var(--space-lg) 0 var(--space-sm);
  color: var(--color-muted);
}}
main#main-content > p {{ margin: 0 0 var(--space-md); color: var(--color-muted); }}
main#main-content > p small {{ font-size: 0.875rem; }}
table.data-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow);
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-md);
}}
table.data-table th,
table.data-table td {{
  padding: var(--space-sm) var(--space-md);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}}
table.data-table th {{
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-accent);
  background: rgba(88, 166, 255, 0.06);
}}
table.data-table tbody tr:last-child td {{ border-bottom: none; }}
table.data-table tbody tr:hover td {{ background: rgba(255, 255, 255, 0.035); }}
canvas[role="img"] {{
  display: block;
  max-width: 100%;
  height: auto;
  margin: var(--space-sm) 0 var(--space-md);
  border-radius: var(--radius-sm);
}}
.network-panel {{
  width: 100%;
  max-width: 800px;
  height: 400px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin: var(--space-sm) 0 var(--space-md);
}}
p.empty-state {{ color: var(--color-muted); font-size: 0.875rem; font-style: italic; }}
footer.dashboard-footer {{
  margin-top: var(--space-xl);
  padding: var(--space-lg) var(--space-md);
  font-size: 0.875rem;
  color: var(--color-muted);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}}
footer.dashboard-footer code {{
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  background: var(--color-bg);
  padding: 0.15em 0.45em;
  border-radius: var(--radius-sm);
  color: var(--color-accent-warm);
}}
.visually-hidden {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }}
/* SR-only chart/network data tables — off-screen, not display:none (AT can navigate tables) */
.sr-only-chart-block,
table.sr-chart-table {{
  position: absolute;
  left: -10000px;
  top: auto;
  width: auto;
  height: auto;
  overflow: visible;
  margin: 0;
}}
.network-region {{
  outline: none;
}}
.network-region:focus-visible {{
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius-md);
}}
/* MW-7 responsive */
@media (max-width: 720px) {{
  main#main-content.dashboard-main {{ padding: var(--space-md) var(--space-sm); }}
  h1 {{
    font-size: clamp(1.2rem, 5.2vw, 1.65rem);
    margin-bottom: var(--space-sm);
  }}
  h2 {{ margin-top: var(--space-lg); margin-bottom: var(--space-sm); }}
  h3 {{ margin-top: var(--space-md); }}
  table.data-table th,
  table.data-table td {{
    padding: var(--space-xs) var(--space-sm);
    font-size: 0.8125rem;
  }}
  .network-panel {{
    height: min(320px, 55vh);
    max-width: 100%;
  }}
  footer.dashboard-footer {{
    padding: var(--space-md) var(--space-sm);
    font-size: 0.8125rem;
  }}
}}
/* MW-6: print — light paper, tables/charts avoid awkward splits; SR data tables visible on paper */
@media print {{
  * {{ animation: none !important; }}
  body.dashboard-body {{
    background: #fff !important;
    color: #000 !important;
    background-image: none !important;
  }}
  main#main-content.dashboard-main {{
    max-width: none;
    padding: 0.35rem 0.5rem;
  }}
  h1, h2, h3 {{ color: #000 !important; }}
  table.data-table {{
    box-shadow: none;
    border: 1px solid #999;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .sr-only-chart-block,
  table.sr-chart-table {{
    position: static !important;
    left: auto !important;
    width: 100% !important;
    height: auto !important;
    overflow: visible !important;
    margin: 0.5rem 0 !important;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  canvas[role="img"],
  .network-panel {{
    break-inside: avoid;
    page-break-inside: avoid;
    max-width: 100%;
  }}
  .network-region:focus-visible {{ outline: none !important; }}
  footer.dashboard-footer {{
    background: #fff !important;
    border-top: 1px solid #ccc;
    color: #333 !important;
  }}
}}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/wordcloud2.js/1.0.2/wordcloud2.min.js"></script>
</head>
<body class="dashboard-body">
<main id="main-content" class="dashboard-main">
<h1>Moltbook Watchtower</h1>
<p>Total posts: <strong>{total_posts}</strong> | Total comments: <strong>{total_comments}</strong> | Total findings: <strong>{total_findings}</strong></p>
<p><small>Last generated: {last_generated}</small></p>

<h2>Findings by rule</h2>
{_captioned_table("Findings by rule", "<tr><th>rule_id</th><th>severity</th><th>count</th></tr>", rows_html)}

<h2>Recent findings (last 50)</h2>
{_captioned_table("Recent findings (last 50)", "<tr><th>post_id</th><th>comment_id</th><th>rule_id</th><th>severity</th><th>redacted_snippet</th><th>created_at</th></tr>", recent_rows)}

<h2>Top submolts by post count</h2>
{_captioned_table("Top submolts by post count", "<tr><th>submolt</th><th>count</th></tr>", submolt_rows)}

<h2>Top agents by posts</h2>
{_captioned_table("Top agents by posts", "<tr><th>agent_name</th><th>count</th></tr>", top_agents_posts_rows)}

<h2>Top agents by comments</h2>
{_captioned_table("Top agents by comments", "<tr><th>agent_name</th><th>count</th></tr>", top_agents_comments_rows)}

<h2>Recent behavior metrics</h2>
{_captioned_table("Recent behavior metrics", "<tr><th>metric_type</th><th>key_name</th><th>value_int</th><th>created_at</th></tr>", behavior_rows)}

<h2>Grounded vs rhetoric (distinct items)</h2>
<p>Items = post or comment with at least one grounded_* or ling_*/drift_* finding.</p>
<h3>Per agent (top 20)</h3>
{_captioned_table("Grounded vs rhetoric: per agent (top 20)", "<tr><th>agent_name</th><th>grounded_items</th><th>rhetoric_items</th><th>total</th></tr>", agent_grounded_rows)}
<h3>Per submolt (top 15)</h3>
{_captioned_table("Grounded vs rhetoric: per submolt (top 15)", "<tr><th>submolt</th><th>grounded_items</th><th>rhetoric_items</th><th>total</th></tr>", submolt_grounded_rows)}
<h3>Trend (findings per day)</h3>
{_captioned_table("Grounded vs rhetoric: trend (findings per day)", "<tr><th>date</th><th>grounded</th><th>rhetoric</th></tr>", grounded_trend_rows)}

<h2>Findings by severity (pie)</h2>
{sr_severity}
<canvas id="chartSeverityPie" width="300" height="200" role="img" aria-label="Chart: findings by severity (pie)" aria-describedby="desc-chartSeverityPie"></canvas>
<p id="emptySeverityPie" class="empty-state" style="display:none">No data for this period</p>

<h2>Posts over time (daily)</h2>
{sr_posts_ot}
<canvas id="chartPostsOverTime" width="400" height="150" role="img" aria-label="Chart: posts over time (daily)" aria-describedby="desc-chartPostsOverTime"></canvas>
<p id="emptyPostsOverTime" class="empty-state" style="display:none">No data for this period</p>

<h2>Findings over time (daily)</h2>
{sr_findings_ot}
<canvas id="chartFindingsOverTime" width="400" height="150" role="img" aria-label="Chart: findings over time (daily)" aria-describedby="desc-chartFindingsOverTime"></canvas>
<p id="emptyFindingsOverTime" class="empty-state" style="display:none">No data for this period</p>

<h2>Behavior metrics over time (daily)</h2>
{sr_behavior_ot}
<canvas id="chartBehaviorOverTime" width="400" height="150" role="img" aria-label="Chart: behavior metrics over time (daily)" aria-describedby="desc-chartBehaviorOverTime"></canvas>
<p id="emptyBehaviorOverTime" class="empty-state" style="display:none">No data for this period</p>

<h2>Findings by rule (bar)</h2>
{sr_findings_rule}
<canvas id="chartFindingsByRule" width="400" height="200" role="img" aria-label="Chart: findings by rule (bar)" aria-describedby="desc-chartFindingsByRule"></canvas>
<p id="emptyFindingsByRule" class="empty-state" style="display:none">No data for this period</p>

<h2>Comments per post (top 10)</h2>
{sr_comments_pp}
<canvas id="chartCommentsPerPost" width="400" height="200" role="img" aria-label="Chart: comments per post (top 10)" aria-describedby="desc-chartCommentsPerPost"></canvas>
<p id="emptyCommentsPerPost" class="empty-state" style="display:none">No data for this period</p>

<h2>Agent activity heatmap (last 14 days)</h2>
<table class="data-table" border="0"><caption class="visually-hidden">{html_lib.escape("Agent activity heatmap (last 14 days)")}</caption><thead><tr><th>Agent</th>{heatmap_header}</tr></thead><tbody>{heatmap_rows_html}</tbody></table>

<h2 id="heading-network-agent-submolt">Network: Agent–Submolt</h2>
<div class="network-region" role="region" aria-labelledby="heading-network-agent-submolt" tabindex="0">
{sr_net}
<p id="networkGraph-keyboard-hint" class="visually-hidden">Interactive graph: use the mouse or touch to pan and zoom. Keyboard graph navigation is limited; use the data tables above for full node and edge lists.</p>
<div id="networkGraph" class="network-panel" role="group" aria-label="Agent and submolt network graph" aria-describedby="desc-networkGraph networkGraph-keyboard-hint"></div>
<p id="emptyNetwork" class="empty-state" style="display:none">No data for this period</p>
</div>

<h2 id="heading-comment-threads">Comment threads (sample)</h2>
<div class="network-region" role="region" aria-labelledby="heading-comment-threads" tabindex="0">
{sr_net_c}
<p id="networkCommentGraph-keyboard-hint" class="visually-hidden">Interactive graph: use the mouse or touch to pan and zoom. Keyboard graph navigation is limited; use the data tables above for full node and edge lists.</p>
<div id="networkCommentGraph" class="network-panel" role="group" aria-label="Comment thread network graph" aria-describedby="desc-networkCommentGraph networkCommentGraph-keyboard-hint"></div>
<p id="emptyNetworkComment" class="empty-state" style="display:none">No data for this period</p>
</div>

<h2>Word cloud: Molts (posts &amp; comments)</h2>
{sr_wc_m}
<canvas id="wordcloudMolts" width="700" height="350" role="img" aria-label="Word cloud: frequent words in molts (posts and comments)" aria-describedby="desc-wordcloudMolts"></canvas>
<p id="emptyWordcloudMolts" class="empty-state" style="display:none">No text data for this period</p>

<h2>Word cloud: Submolts (names &amp; descriptions)</h2>
{sr_wc_s}
<canvas id="wordcloudSubmolts" width="700" height="300" role="img" aria-label="Word cloud: submolt names and descriptions" aria-describedby="desc-wordcloudSubmolts"></canvas>
<p id="emptyWordcloudSubmolts" class="empty-state" style="display:none">No submolt data for this period</p>
</main>

<script type="application/json" id="dashboardData">{data_json}</script>
<script id="dashboard-runtime">
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
<footer class="dashboard-footer">
<p>Bulk / offline network data: run <code>python scripts/export_network.py</code> from the repo (writes <code>exports/network_edges.csv</code> and <code>exports/network.graphml</code> beside your DB). See <code>docs/TELEMETRY_AND_NETWORK_VIZ.md</code> for Gephi, NodeXL, Cytoscape, and other tools.</p>
</footer>
</body>
</html>
"""
    exports = settings.db_path.parent / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    path = exports / "dashboard.html"
    path.write_text(html_document, encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
