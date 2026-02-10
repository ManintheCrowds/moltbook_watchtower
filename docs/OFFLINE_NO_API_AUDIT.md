# Moltbook Watchtower — Run Without API: Audit

Audit of what’s needed to run Watchtower without the Moltbook API, plus development gaps, inefficiencies, and bugs.

---

## 1. What’s needed to run without the API

### 1.1 Current dependency

- **Only `scripts/run_collector.py`** needs the API. It calls `get_settings(require_api_key=True)` and uses `MoltbookClient` to fetch posts, feed, submolts, and comments.
- All other entrypoints use `get_settings(require_api_key=False)` and read/write only DB, files, and audit log.

### 1.2 “No-API” workflow (today)

| Step | Script | Needs API? | Notes |
|------|--------|------------|--------|
| Collect | `run_collector.py` | **Yes** | **Skip this** when running without API. |
| Analyze | `run_analyzers.py` | No | Reads from DB. |
| Report | `report_summary.py` | No | Reads from DB. |
| Dashboard | `generate_dashboard_html.py` | No | Reads from DB. |
| Export | `export_network.py` | No | Reads from DB. |
| Canary | `check_canary.py` | No | No API. |
| Daily entrypoint | `run_daily.py` | No (collector step skipped if no key) | If `MOLTBOOK_API_KEY` is unset, skips collect; still runs analyzers, report, dashboard, export, and (if `OLLAMA_ENABLED`) LLM summary. |

To run without the API:

1. **Do not run** `run_collector.py`.
2. **Ensure data is already in the DB** (from a previous collect, or from an import — see below).
3. Run in order:  
   `run_analyzers.py` → `report_summary.py` → `generate_dashboard_html.py` → (optional) `export_network.py`.

No code change is required for this “existing DB only” mode. The gap is **documentation** and, if you want to add data offline, an **import path**.

### 1.3 Optional: adding data without the API

There is **no script** to ingest from file (e.g. JSON). The integration test builds a fixture DB by calling `StorageWriter.write_posts_response`, `write_post_comments`, and `insert_findings` with in-memory structures matching the API response shape.

**Development needed (optional):**

- **`scripts/import_from_json.py`** (or similar): read JSON file(s) in the same shape as the API (posts list or `{ "posts" | "data" | "results": [...] }`, submolts, comments per post), then call:
  - `writer.write_posts_response(body)`
  - `writer.write_submolts_response(body)` (if you have submolts)
  - `writer.write_post_comments(post_id, body)` per post  
  So you can backfill or use dumps from another source without calling the API.

---

## 2. Development needed

| Item | Priority | Description |
|------|----------|-------------|
| **Document “offline / no-API” mode** | High | In README and/or runbook: when API is unavailable or undesired, skip collector; run analyzers → report → dashboard (and optionally export). Require existing DB. |
| **Import-from-JSON script** | Medium | Allow ingesting posts/submolts/comments from JSON (API-shaped) so data can be added without the live API. Reuse `StorageWriter`; no new schema. |
| **LOG_DIR creation** | Low | `audit_log()` already does `log_path.parent.mkdir(parents=True, exist_ok=True)`. Scripts that only use `get_settings(require_api_key=False)` never create `LOG_DIR` unless they call `audit_log` (e.g. `run_analyzers` does). If you add a “no-API” entrypoint that never calls `audit_log`, ensure `LOG_DIR` exists or document that it’s created on first collect/analyzer run. |

---

## 3. Inefficiencies

| Location | Issue | Recommendation |
|----------|--------|----------------|
| **`run_collector.py`** | Opens many DB connections: 2× `write_posts_response`, 1× `write_submolts_response`, N× `write_post_comments`. | Use a single connection for the whole run: e.g. one `get_connection` at start, pass conn into writer methods, or add `StorageWriter` batch helpers that accept an optional `conn`. |
| **`StorageWriter`** | Each `write_*` and `insert_findings` opens and closes its own connection. | Add a context API or optional `conn` parameter so a single connection can be reused for a batch of writes (collector run, or import script). |

---

## 4. Bugs and edge cases

| Area | Finding | Severity | Suggestion |
|------|---------|----------|------------|
| **Writer body type** | `write_posts_response(body)`, `write_submolts_response(body)`, `write_post_comments(post_id, body)` assume `body` is `list` or `dict`. If API (or import) passes a string or other type, `body.get(...)` raises. | Low | At the start of each `write_*`, add: `if not isinstance(body, (list, dict)): return 0`. |
| **Empty DB** | All no-API scripts (analyzers, report, dashboard, export) run correctly on an empty DB: they return 0 counts and empty tables/files. | None | No change. |
| **run_collector exception handler** | On any exception (e.g. network, API error), the handler calls `get_settings(require_api_key=False)` for audit_log and send_alert. If the failure was “missing API key”, the initial `get_settings(require_api_key=True)` raised before client use; the except block still gets settings and logs/alerts. | None | Correct as is. |
| **BehaviorAnalyzer INSERT** | `conn.execute(..., ("posts_per_agent_window", agent_name or "", cnt))` — 3 placeholders and 3 values; SQL uses `datetime('now')` for the 4th column. | None | Correct. |
| **report_summary daily_report_dir** | Uses `getattr(settings, "daily_report_dir", None)`. `Settings` has `daily_report_dir` in `__slots__`, so attribute always exists. | None | No change. |

No critical or high-severity bugs found. The only suggested hardening is defensive handling of non–list/dict `body` in the writer.

---

## 5. Summary

- **To run without the API:** Don’t run `run_collector.py`; run the rest against an existing DB. No code change required; document this “offline” flow.
- **Optional:** Add `import_from_json.py` (or equivalent) to load API-shaped JSON into the DB so you can add data without the API.
- **Inefficiencies:** Collector and writer open many DB connections per run; batching or a single-connection path would reduce overhead.
- **Bugs:** None critical. Consider normalizing writer input (reject non–list/dict `body` with an early return 0).

---

## 6. Quick reference — no-API sequence

```bash
# No .env API key required. DATA_DIR must point to a dir with existing watchtower.db.
python scripts/run_analyzers.py
python scripts/report_summary.py
python scripts/generate_dashboard_html.py
python scripts/export_network.py   # optional
# Outputs: exports/summary_report.md, exports/dashboard.html, exports/network_edges.csv, exports/network.graphml
```

Or use the single daily entrypoint without an API key (collector is skipped; LLM summary still runs if `OLLAMA_ENABLED` is set):

```bash
python scripts/run_daily.py
```

If the DB is empty, you get zero counts and empty reports/dashboard/export until data is added (e.g. by a future import script or a prior collect when the API was available).
