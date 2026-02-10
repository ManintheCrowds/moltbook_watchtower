# Runbook: Collector API failure (non-zero exit)

## When

Collector script (`run_collector.py`) exits with code 1: fetch_error or repeated non-200 from Moltbook API.

## Steps

1. **Check audit log** (no raw content; metadata only):
   - Path: `$LOG_DIR/audit.jsonl` (default `logs/audit.jsonl`).
   - Look for recent `fetch_error` or `fetch_*_error` events; note `status`, `endpoint`, `extra.error_type`.

2. **Verify API key:**
   - `MOLTBOOK_API_KEY` must be set (e.g. in `.env`).
   - Key must be valid and for a claimed watchdog agent. See [Moltbook skill.md](https://www.moltbook.com/skill.md) — Register First, Check Claim Status.

3. **Verify base URL:**
   - We only send the key to `https://www.moltbook.com` (with www). Redirects without www can strip Authorization; ensure no proxy or env overrides base URL.

4. **Rate limits:**
   - If audit shows 429 on specific endpoints, see [incident-rate-limit.md](incident-rate-limit.md).
   - Reduce `COMMENT_FETCH_LIMIT` or run less frequently.

5. **Network / API availability:**
   - Confirm Moltbook is reachable (e.g. `curl -s -o /dev/null -w "%{http_code}" "https://www.moltbook.com/api/v1/submolts" -H "Authorization: Bearer $MOLTBOOK_API_KEY"`). Expect 200 when key is valid.

6. **Retry:**
   - After fixing key or network, run collector again: `python scripts/run_collector.py`.

## Optional: Signal alert

If Signal alerting is configured, collector failure can trigger `send_alert("Watchtower collector failed", summary)`. See Signal runbook note in docs.
