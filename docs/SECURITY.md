# Security — Our End

How we handle secrets, data, and logging so the Watchtower itself stays low-risk.

**AI security:** For MVP AI security and Zero Trust when integrating generative AI, see [D:\local-first\AI_SECURITY.md](D:\local-first\AI_SECURITY.md). This repo monitors agent networks; it does not run generative AI.

## API key

- **Location:** Environment variable `MOLTBOOK_API_KEY` only. No keys in repo or config files.
- **Scope:** The key is sent **only** to `https://www.moltbook.com`. Code validates the base URL before attaching the `Authorization: Bearer` header. Never send this key to any other host (e.g. webhooks, third-party APIs, or "verification" services).
- **Use:** Single "watchdog" agent. Read-only GET requests; no POST (no posting, commenting, or upvoting).
- **Agent naming:** When registering the Moltbook agent, use a neutral name and description (e.g. research or community interest). Do not use names or descriptions that advertise monitoring, auditing, or security scanning so the client does not stand out.

## Storage

- **Database:** SQLite under `data/` (gitignored). The DB may contain content that includes **leaked credentials** from other agents. Treat it as sensitive: restrict filesystem access, encrypt backups if needed.
- **No cloud in v1:** All storage is local. If you add cloud later, use access controls and encryption.

## Logging

- **We do not log** raw post/comment content or full API responses. Log only: timestamps, endpoint, HTTP status, record counts, and redacted identifiers (e.g. `post_id=abc123`, agent name).
- **Leak alerts:** Log "leak detected, post_id=X, rule=Y" — never the actual secret. Optionally store a redacted snippet (e.g. `Bearer ***`) for debugging.

## Alerts

- Alert payloads (file, Slack, email) include post ID and rule name, not the secret. Redacted snippets only.

## Audit trail

- Dedicated audit log (e.g. `logs/audit.jsonl`) for our actions: each fetch (endpoint, time, status, count), each analyzer run, each alert. No content in the audit log.

## Operational

- **DB file permissions:** Restrict access to `data/` and the DB file (e.g. `chmod 600` on the DB, or restrict the `data/` directory to the process user). The DB may contain leaked credentials from collected content.
- **Dashboard:** Do not serve `exports/dashboard.html` from a public or shared web server. Open only locally (file:// or localhost-only if you ever add a minimal server). The dashboard may contain aggregated metadata and redacted findings.## Local verification

Before first push, run `gitleaks detect --source . --config .gitleaks.toml --no-git` from repo root (or use `.cursor/scripts/run_gitleaks_three_roots.ps1` from portfolio-harness). CI runs gitleaks on push/PR; local run catches issues earlier.

## Audit summary**What we have:** API key in env only; key sent only to `https://www.moltbook.com` (validated in client); read-only GET; 90 req/min; audit log with endpoint/status/count/ts (no content); optional Signal alert on collector exception; SQLite under `data/` (gitignored); static dashboard to `exports/` (no server); neutral agent naming guidance; optional cron jitter; runbooks for daily cron, API failure, rate limit, add analyzer, Signal.**Exposure surface:** Outbound — only Moltbook API (Bearer + User-Agent). Inbound — none (no HTTP server). Local — `data/`, `logs/`, `exports/` gitignored but on disk; DB holds post/comment content and redacted findings (sensitive).