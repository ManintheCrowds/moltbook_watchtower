# Moltbook Watchtower — Setup and Go Live

## Pending: Moltbook API key

Obtain a Moltbook API key by registering a **watchdog agent** (read-only) per [Moltbook skill.md](https://www.moltbook.com/skill.md) — see **Register First**:

1. `POST https://www.moltbook.com/api/v1/agents/register` with `{"name": "YourWatchdogName", "description": "Read-only monitoring"}`.
2. Save the returned `api_key` immediately.
3. Have your human claim the agent via the `claim_url` (verification tweet).
4. Store the key in `.env` as `MOLTBOOK_API_KEY=your_key`. Never commit `.env`.

If you cannot get a key immediately (e.g. claim pending), treat this as a pending task; the collector will fail until the key is set and valid.

## Go live

**Go live** means:

1. **API key set** — `MOLTBOOK_API_KEY` in `.env` (watchdog agent claimed).
2. **Run collector against live API** — `python scripts/run_collector.py` (fetches posts, feed, submolts, comments).
3. **Run analyzers** — `python scripts/run_analyzers.py` (leak, injection, behavior).
4. **Open dashboard** — `python scripts/generate_dashboard_html.py` then open `exports/dashboard.html` in a browser to verify data in tables and graphs.

Optional: run report for summary markdown — `python scripts/report_summary.py`. For daily cron and env vars, see [runbooks/daily-collect-and-report.md](runbooks/daily-collect-and-report.md).

## Reference

- [Moltbook skill.md](https://www.moltbook.com/skill.md) — canonical API documentation (endpoints, rate limits, response shapes).
- [MOLTBOOK_API_AUDIT.md](MOLTBOOK_API_AUDIT.md) — mapping of our client/writer/collector to skill.md.
