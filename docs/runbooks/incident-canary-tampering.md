# Runbook: Incident — Canary tampered

## When this runs

The canary alert fires when `python scripts/check_canary.py` detects that `data/.canary` is missing or its SHA-256 no longer matches the expected value (from `data/.canary.sha256` or env `WATCHTOWER_CANARY_SHA256`). Assume possible compromise or unintended tampering.

## Steps

1. **Assume compromise** until proven otherwise. Do not ignore the alert.
2. **Rotate the real API key:** Revoke or regenerate the Moltbook watchdog agent key. Update `MOLTBOOK_API_KEY` in `.env` (or wherever it is set). Ensure no code uses the honeypot key from `config/env.honeypot.sample`.
3. **Check audit log:** Review `logs/audit.jsonl` for recent `auth_failure`, `fetch_*_error`, or unusual endpoints/timestamps.
4. **Check process list and access:** On the host, review who/what could have modified `data/` (e.g. other users, cron jobs, backup tools that delete or overwrite files).
5. **Review recent changes:** If using version control, check for recent commits or deploys that might have recreated or changed `data/`. Confirm no unauthorized code or config changes.
6. **Restore or regenerate canary:**
   - If tampering was benign (e.g. you recreated `data/` or ran a script that removed the canary): run `python scripts/check_canary.py --init` to create a new canary and update `data/.canary.sha256`. If you use `WATCHTOWER_CANARY_SHA256`, update the env with the new hash printed by `--init`.
   - If you have a known-good backup of `data/.canary` and `data/.canary.sha256`, restore them and re-run the check.
7. **Resume normal runs** only after the canary check passes and you are satisfied that the cause was identified and mitigated.

## Reference

- Canary setup: [daily-collect-and-report.md](daily-collect-and-report.md) — Canary (tripwire).
- Security overview: [SECURITY.md](../SECURITY.md).
