# Runbook: Rate limit (429) from Moltbook API

## When

Audit log shows `status: 429` for one or more requests (e.g. fetch_posts, fetch_feed, fetch_comments).

## Moltbook limits (skill.md)

- 100 requests/minute (general).
- Post/comment creation has additional cooldowns (we do not POST).

## Steps

1. **Confirm 429 in audit:** Check `logs/audit.jsonl` for `"status": 429` and `endpoint` to see which call was limited.

2. **Reduce comment fetch volume:**
   - We fetch comments for the latest N posts each run. Default N = 25 (`COMMENT_FETCH_LIMIT`).
   - Set a lower value: `COMMENT_FETCH_LIMIT=10` (or 15, 20) so each run uses fewer GETs.
   - Env: `export COMMENT_FETCH_LIMIT=10` or add to `.env`.

3. **Run less frequently:**
   - If running collector multiple times per day, increase the interval (e.g. once daily) to stay under 100/min over the day.

4. **Client behavior:**
   - Our client already backs off on 429: waits `Retry-After` (capped) and retries. If 429 persists, the run may still exit; reduce load as above and retry later.

5. **Retry:** After reducing `COMMENT_FETCH_LIMIT` or frequency, run collector again: `python scripts/run_collector.py`.
