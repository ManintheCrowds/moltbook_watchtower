# Runbook: Daily collect and report

## Purpose

Run the Moltbook Watchtower collector, analyzers, summary report, and optionally the dashboard on a schedule (e.g. daily). Produces DB updates, findings, and reports.

## Prerequisites

- `MOLTBOOK_API_KEY` set (e.g. in `.env`). See [Moltbook skill.md](https://www.moltbook.com/skill.md) — Register First.
- Python env with dependencies: `pip install -r requirements.txt`.
- From repo root: `config`, `src`, and `scripts` on path (or run scripts from repo root).

## Single daily entrypoint

For scheduled runs, use one script that runs the full pipeline in order:

```bash
python scripts/run_daily.py
```

Environment variables control which steps run:

| Variable | Default | Description |
|----------|---------|-------------|
| RUN_CANARY | (unset) | If set to 1, true, or yes, run canary check first; daily run exits on canary failure. |
| MOLTBOOK_API_KEY | (unset) | If set, run collector before analyzers; if unset, skip collect (offline mode). |
| OLLAMA_ENABLED | (unset) | If set to 1, true, or yes, run Ollama daily summary after export (best-effort; does not fail run). |
| OLLAMA_MODEL | llama3.2 | Model name for Ollama (e.g. llama3.2, mistral). |
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama API base URL. |
| OLLAMA_TIMEOUT_SECONDS | 120 | Timeout for Ollama generate request. |

See also: [Daily LLM summary (Ollama)](#daily-llm-summary-ollama) below.

## Environment variables (all scripts)

| Variable | Default | Description |
|----------|---------|-------------|
| MOLTBOOK_API_KEY | (required for collector) | Watchdog agent API key; read-only GET only. |
| DATA_DIR | data | Directory for SQLite DB. |
| LOG_DIR | logs | Directory for audit log. |
| JITTER_SECONDS | 0 | Optional delay 0–120s at start (e.g. 60 for cron). |
| COMMENT_FETCH_LIMIT | 25 | Max posts to fetch comments for per run (1–50). |
| DAILY_REPORT_DIR | (unset) | If set (e.g. reports/daily), write date-named report here. See `scripts/report_summary.py`. |

## Canary (tripwire)

Optional: detect tampering of the data dir. One-time setup:

```bash
python scripts/check_canary.py --init
```

This creates `data/.canary` (random blob) and `data/.canary.sha256` (expected hash). Optionally set `WATCHTOWER_CANARY_SHA256` in env to override the hash file.

To verify before each collect (optional), run `python scripts/check_canary.py` before the collector in cron. On mismatch or missing canary, the script alerts (Signal if enabled) and exits non-zero. See [incident-canary-tampering.md](incident-canary-tampering.md) if the alert fires.

## Honeypot (bait) file

`config/env.honeypot.sample` contains a fake `MOLTBOOK_API_KEY` for honeypot use only. **No Watchtower code must ever read or use this file.** If this key appears in Moltbook logs or support requests, assume the project is compromised and rotate the real API key. See [SECURITY.md](../SECURITY.md).

## Cron sequence

Example: run once daily at 08:00. Use the single entrypoint so collector (if API key set), analyzers, report, dashboard, export, and optional Ollama summary all run in order.

```bash
# Crontab example (run from repo root)
0 8 * * * cd /path/to/moltbook-watchtower && JITTER_SECONDS=60 RUN_CANARY=1 python scripts/run_daily.py
```

Optional: set `OLLAMA_ENABLED=1` and `OLLAMA_MODEL=llama3.2` in the cron environment to enable the daily LLM summary (requires Ollama installed and running).

Steps inside `run_daily.py` (in order):

1. **Canary (optional):** If `RUN_CANARY=1`, run `check_canary.py`; exit on failure.
2. **Collect (optional):** If `MOLTBOOK_API_KEY` is set, run `run_collector.py` — fetches posts, feed, submolts, comments. Writes to DB.
3. **Analyze:** `run_analyzers.py` — leak, injection, behavior analyzers; findings to DB and `exports/alerts.txt`.
4. **Report:** `report_summary.py` — `exports/summary_report.md` and optionally `DAILY_REPORT_DIR/YYYY-MM-DD.md`.
5. **Dashboard:** `generate_dashboard_html.py` — `exports/dashboard.html`.
6. **Export:** `export_network.py` — `exports/network_edges.csv`, `exports/network.graphml`.
7. **Summary (optional):** If `OLLAMA_ENABLED=1`, run `generate_daily_summary.py` — writes narrative to `DAILY_REPORT_DIR/YYYY-MM-DD-summary.md` (or `exports/`). Failure does not fail the daily run.

## DB backup

Before major upgrades, copy the DB. Encrypt backups if storing off-host (e.g. `gpg -c watchtower.db.bak`, or 7z with password, or OS-level encryption):

```bash
cp "$DATA_DIR/watchtower.db" "$DATA_DIR/watchtower.db.bak.$(date +%Y%m%d)"
# Optional: encrypt before moving off-host
# gpg -c "$DATA_DIR/watchtower.db.bak.$(date +%Y%m%d)"
```

## DB and directory permissions

Restrict access so only the process user can read `data/`, `logs/`, and `exports/`. On Unix: `chmod 700 data/ logs/ exports/` and `chmod 600 data/watchtower.db`. On Windows: restrict the directories to the run-as user (e.g. via Properties → Security). The DB may contain leaked credentials from findings.

## Run without API (offline)

When the API is unavailable or you prefer not to call it (e.g. no key yet, or using existing DB only):

1. **Do not set** `MOLTBOOK_API_KEY`, or run without it. Then `run_daily.py` skips the collector and runs analyzers, report, dashboard, export, and (if enabled) Ollama summary.
2. Or run the offline-only sequence: `python scripts/run_offline.py`, or manually: `run_analyzers.py` then `report_summary.py` then `generate_dashboard_html.py` then `export_network.py`.

No `MOLTBOOK_API_KEY` is required. Data must already be in the DB (from a prior collect or import). Outputs: `data/exports/summary_report.md`, `data/exports/dashboard.html`, and optionally `data/exports/network_edges.csv`, `data/exports/network.graphml`. See [OFFLINE_NO_API_AUDIT.md](../OFFLINE_NO_API_AUDIT.md).

## Windows Task Scheduler

To run the daily pipeline on Windows:

1. Open Task Scheduler → Create Basic Task (or Create Task).
2. Trigger: Daily at the desired time (e.g. 08:00).
3. Action: Start a program. Program: `python` (or full path to your Python executable). Add arguments: `D:\path\to\moltbook-watchtower\scripts\run_daily.py`. Start in: `D:\path\to\moltbook-watchtower`.
4. Set environment variables in the task (Task → Properties → General → "Run with highest privileges" if needed; for env vars use a wrapper script). Alternatively, create a batch or PowerShell script that sets `DATA_DIR`, `LOG_DIR`, `MOLTBOOK_API_KEY` (if used), `OLLAMA_ENABLED`, `OLLAMA_MODEL`, and then runs `python scripts\run_daily.py` from the repo root.

Example PowerShell wrapper (save as `run_daily.ps1` in repo root):

```powershell
$env:DATA_DIR = "D:\path\to\moltbook-watchtower\data"
$env:LOG_DIR = "D:\path\to\moltbook-watchtower\logs"
# $env:MOLTBOOK_API_KEY = "your-key"
# $env:OLLAMA_ENABLED = "1"
# $env:OLLAMA_MODEL = "llama3.2"
Set-Location "D:\path\to\moltbook-watchtower"
python scripts\run_daily.py
```

Schedule the wrapper script in Task Scheduler (Program: `powershell.exe`, Arguments: `-File D:\path\to\moltbook-watchtower\run_daily.ps1`).

## Daily LLM summary (Ollama)

Optional: generate a short narrative summary of the day's counts, findings, and post highlights using a self-hosted Ollama model.

**Requirements:**

- Ollama installed and running (e.g. `ollama serve`; often running as a service). Pull a model: `ollama pull llama3.2`.
- Set `OLLAMA_ENABLED=1` (or `true`/`yes`) and optionally `OLLAMA_MODEL=llama3.2`, `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_TIMEOUT_SECONDS=120`.

**Output:** `DAILY_REPORT_DIR/YYYY-MM-DD-summary.md` (or `data/exports/YYYY-MM-DD-summary.md` if `DAILY_REPORT_DIR` is unset). The prompt uses only counts, finding rule/severity/redacted snippets, and post title + truncated snippet (no raw secrets).

**Behavior when Ollama is down:** The summary step is best-effort. If Ollama is unreachable or returns an error, the script logs and exits 0; the daily run does not fail. No summary file is written (or you can extend the script to write a "Summary skipped (Ollama unavailable)" placeholder).

## Failure handling

- If collector exits non-zero: see [incident-api-failure.md](incident-api-failure.md).
- If you see 429 (rate limit): see [incident-rate-limit.md](incident-rate-limit.md).
