# Telemetry and Network Visualization

This doc describes how Watchtower visualizes telemetry (tables, charts, in-dashboard graph) and how to export network data for external tools (Gephi, NodeXL, Cytoscape, etc.). We do not log or export raw post/comment content; only IDs, counts, and metadata.

## Current dashboard (tables + Chart.js)

- **Script:** `scripts/generate_dashboard_html.py` → `exports/dashboard.html` (single static HTML).
- **KPIs:** Total posts, comments, findings; last generated timestamp.
- **Tables:** Findings by rule/severity, recent findings (50), top submolts by post count, top agents by posts, top agents by comments, recent behavior metrics.
- **Charts (Chart.js):** Posts per day (line), findings per day (line), findings by rule (bar), comments per post top 10 (bar), severity pie, behavior over time.
- **Word clouds (wordcloud2.js):** “Molts” from post titles + content and comment content (top 80 terms, stopwords removed); “Submolts” from submolt names (weighted by post count), display names, and descriptions (top 50 terms). Helps quickly see dominant topics and submolt vocabulary.
- **Data source:** JSON embedded in the HTML; no server. Chart and word-cloud containers show empty-state messages when data is absent.

## In-dashboard network graph (Option A)

The same dashboard includes an **agent–submolt** force-directed graph: agents linked to submolts they post in; edge weight = post count. Rendered with **vis-network** (CDN) in the same HTML file. Data: `network_nodes` and `network_edges` in the embedded JSON. See `scripts/generate_dashboard_html.py` for the graph payload and the "Network: Agent–Submolt" section.

## Export for external tools (Option B)

- **Script:** `scripts/export_network.py` reads from the same SQLite DB and writes to `exports/` (gitignored):
  - **Edge list CSV:** `exports/network_edges.csv` — columns `source,target,weight,edge_type`. Edges: agent→submolt (weight = post count, type `posts_in`), comment→post (type `comment_on_post`), comment→parent comment (type `reply_to_comment`). Comment edges are capped (e.g. last 5000) to keep file size bounded.
  - **GraphML:** `exports/network.graphml` — nodes with `label` and `type` (agent/submolt/post/comment); edges with `weight` and `edge_type`. Compatible with Gephi, Cytoscape, and others that support GraphML.

Run: `python scripts/export_network.py` (no API key required). Then open the CSV or GraphML in your tool of choice.

## Mapping to external network tools

Reference: [16 network visualization tools that you should know](https://medium.com/@vespinozag/16-network-visualization-tools-that-you-should-know-2c26957b707e) (Dr. Verónica Espinoza, Medium, Nov 2023). Use for tool choice and "export and open" workflow; credit as in the article.

| Use case | Tool | How to use our export |
|----------|-----|------------------------|
| Force-directed exploration, community detection | **Gephi** / **Gephi Lite** | Import `network_edges.csv` (File → Import Spreadsheet) or `network.graphml`. Run layout (e.g. Force Atlas 2), run statistics (modularity, etc.). |
| Social network analysis (SNA), influencer detection, time series | **NodeXL (Pro)** | Import edge list CSV or GraphML. Use for agent–submolt and comment-thread analysis. |
| Directed graphs, comment reply threads, attribute-rich | **Cytoscape** | Import `network.graphml`. Use for reply chains (comment→comment) and node types. |
| Centrality, layouts, load from file | **SocNetV** | Load GraphML or edge list (supported formats: GraphML, EdgeList, etc.). |
| Share or explore large graphs in browser | **Retina** / **Cosmograph** | Upload or open exported file per tool docs (e.g. Cosmograph: open local file). |
| Co-occurrence / bibliometric-style clustering | **VOSviewer** | More for term co-occurrence; we could later add "co-finding" or "same-submolt" clusters if useful. |

Other tools from the 16 (Graphia, Tulip, Orange, Kumu, Graphext, etc.) that accept edge list or GraphML can consume our export the same way.

## Dashboard development roadmap

Development paths for visual representations are prioritized by impact vs effort. The dashboard remains static HTML with embedded JSON unless noted.

| Path | Description | Effort | Priority |
|------|-------------|--------|----------|
| **A** | Severity pie, behavior-over-time line, agent heatmap, empty-state messages for all charts/tables | Low | Done |
| **B** | Comment-thread network view (bounded), findings overlay or findings-by-post mini-graph, agent–agent radial | Medium | Next: comment-thread / findings overlay |
| **C** | Time range filter (7d/30d/All), drill-down from network (click agent/submolt → table), export graph as PNG | Medium | As needed |
| **D** | Sankey (agent→submolt→volume), small multiples (one line per submolt), radial/clock (activity by hour/weekday) | Higher | Nice-to-have |

Recommended order for MVS: Path A (empty states + severity/behavior charts + heatmap) first, then Path B (comment-thread or findings overlay), then Path C as needed. See the plan file for full details.

## Privacy and content

We do not log or export raw post/comment content. Exported graphs use node IDs (agent name, submolt name, post id, comment id) and edge weights/counts only. Redacted findings (snippet only) are in the dashboard and report, not in the network export.
