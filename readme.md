# Moltbook Watchtower

Passive, read-only monitoring for the Moltbook (OpenClaw) agent network: collect posts and comments, run leak/injection/behavior analyzers, and view findings in a static dashboard. No posting or writing to Moltbook.

- **Setup and go live:** [docs/SETUP.md](docs/SETUP.md) — API key (pending until claimed), go-live steps, link to [Moltbook skill.md](https://www.moltbook.com/skill.md).
- **Security and ethics:** [docs/SECURITY.md](docs/SECURITY.md), [docs/MOLTBOOK_ETHICS.md](docs/MOLTBOOK_ETHICS.md).
- **Runbooks:** [docs/runbooks/](docs/runbooks/) — daily collect-and-report, incidents, Signal alerting, add analyzer.
- **API audit:** [docs/MOLTBOOK_API_AUDIT.md](docs/MOLTBOOK_API_AUDIT.md) — endpoints and response handling vs skill.md.
- **Scheduled runs:** Use `python scripts/run_daily.py` for the full daily pipeline (optional collector, analyzers, report, dashboard, export, and optional [Ollama](https://ollama.ai) narrative summary). See runbook for cron and Windows Task Scheduler. Set `OLLAMA_ENABLED=1` and pull a model (e.g. `ollama pull llama3.2`) for the daily LLM summary.

## Quick start

1. Copy `.env.example` to `.env` and set `MOLTBOOK_API_KEY` (see [docs/SETUP.md](docs/SETUP.md)).
2. `pip install -r requirements.txt`
3. From repo root: `python scripts/run_collector.py` then `python scripts/run_analyzers.py` then `python scripts/generate_dashboard_html.py`.
4. Open `exports/dashboard.html` (or serve it) to view tables and charts.

**Offline / no API:** If you already have a DB (e.g. from a previous collect) and don't want to call the Moltbook API, run only the analysis and report steps — no `MOLTBOOK_API_KEY` needed:

```bash
python scripts/run_analyzers.py
python scripts/report_summary.py
python scripts/generate_dashboard_html.py
python scripts/export_network.py   # optional
```

Or use the convenience script: `python scripts/run_offline.py`. Outputs go to `data/exports/` (or `$DATA_DIR/exports/`). See [docs/OFFLINE_NO_API_AUDIT.md](docs/OFFLINE_NO_API_AUDIT.md) for details.

## Testing

From repo root: `pytest tests/ -v` (or `python -m pytest tests/ -v`).

## Layout

- `config/` — env-based settings (API key, paths, optional Signal, daily report dir).
- `src/client/` — read-only Moltbook API client (GET only, rate limited).
- `src/storage/` — SQLite schema and writer (posts, comments, findings).
- `src/analyzers/` — leak, injection, behavior analyzers.
- `src/alerting/` — Signal alert stub (optional).
- `src/scheduler/` — audit log (metadata only, no content).
- `src/summary/` — daily data, prompt builder, Ollama client for optional LLM summary.
- `scripts/` — run_collector, run_analyzers, report_summary, generate_dashboard_html, run_daily, generate_daily_summary.
