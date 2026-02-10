#!/usr/bin/env python3
# PURPOSE: Export agent-submolt (and optional comment-thread) network from DB for external tools.
# DEPENDENCIES: config, src.storage
# MODIFICATION NOTES: IDs and counts only; no post/comment body. Writes to exports/ (gitignored).

import csv
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.storage import get_connection


def _graphml_escape(s: str) -> str:
    """Escape for GraphML attribute text."""
    if s is None:
        return ""
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main() -> None:
    settings = get_settings(require_api_key=False)
    conn = get_connection(settings.db_path)
    cur = conn.cursor()
    try:
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
        cur.execute(
            """
            SELECT id, post_id, parent_id FROM comments
            WHERE post_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 5000
            """
        )
        comment_edges = [(r[0], r[1], r[2]) for r in cur.fetchall()]
    finally:
        conn.close()

    exports = settings.db_path.parent / "exports"
    exports.mkdir(parents=True, exist_ok=True)

    # Edge list CSV: source,target,weight,edge_type (max compatibility: Gephi, NodeXL, SocNetV, etc.)
    edges_csv = exports / "network_edges.csv"
    with open(edges_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "weight", "edge_type"])
        for agent, submolt, cnt in agent_submolt_edges:
            w.writerow([agent, submolt, cnt, "posts_in"])
        for cid, post_id, parent_id in comment_edges:
            w.writerow([cid, post_id, 1, "comment_on_post"])
            if parent_id:
                w.writerow([cid, parent_id, 1, "reply_to_comment"])
    print(f"Wrote {edges_csv} ({len(agent_submolt_edges)} agent-submolt edges, {len(comment_edges)} comment edges)")

    # GraphML (nodes + edges with attributes for Gephi/Cytoscape)
    graphml_path = exports / "network.graphml"
    node_ids = set()
    for agent, submolt, _ in agent_submolt_edges:
        node_ids.add(("agent", agent))
        node_ids.add(("submolt", submolt))
    for cid, post_id, parent_id in comment_edges:
        node_ids.add(("comment", cid))
        node_ids.add(("post", post_id))
        if parent_id:
            node_ids.add(("comment", parent_id))

    with open(graphml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        f.write('  <key id="label" for="node" attr.name="label" attr.type="string"/>\n')
        f.write('  <key id="type" for="node" attr.name="type" attr.type="string"/>\n')
        f.write('  <key id="weight" for="edge" attr.name="weight" attr.type="int"/>\n')
        f.write('  <key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>\n')
        f.write('  <graph id="G" edgedefault="directed">\n')
        for ntype, nid in sorted(node_ids, key=lambda x: (x[0], x[1])):
            node_id = f"{ntype}_{nid}"
            f.write(f'    <node id="{_graphml_escape(node_id)}">')
            f.write(f'<data key="label">{_graphml_escape(nid)}</data><data key="type">{_graphml_escape(ntype)}</data></node>\n')
        edge_id = 0
        for agent, submolt, cnt in agent_submolt_edges:
            sid, tid = f"agent_{agent}", f"submolt_{submolt}"
            f.write(f'    <edge id="e{edge_id}" source="{_graphml_escape(sid)}" target="{_graphml_escape(tid)}">')
            f.write(f'<data key="weight">{cnt}</data><data key="edge_type">posts_in</data></edge>\n')
            edge_id += 1
        for cid, post_id, parent_id in comment_edges:
            sid, tid = f"comment_{cid}", f"post_{post_id}"
            f.write(f'    <edge id="e{edge_id}" source="{_graphml_escape(sid)}" target="{_graphml_escape(tid)}">')
            f.write(f'<data key="weight">1</data><data key="edge_type">comment_on_post</data></edge>\n')
            edge_id += 1
            if parent_id:
                sid, tid = f"comment_{cid}", f"comment_{parent_id}"
                f.write(f'    <edge id="e{edge_id}" source="{_graphml_escape(sid)}" target="{_graphml_escape(tid)}">')
                f.write(f'<data key="weight">1</data><data key="edge_type">reply_to_comment</data></edge>\n')
                edge_id += 1
        f.write("  </graph>\n</graphml>\n")
    print(f"Wrote {graphml_path}")


if __name__ == "__main__":
    main()
