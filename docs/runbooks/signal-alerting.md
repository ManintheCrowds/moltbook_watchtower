# Runbook: Signal alerting (optional)

## Purpose

When collector or other critical steps fail, optionally send an alert to Signal. Framework only; you plug in your mechanism (e.g. signal-cli or a webhook).

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| SIGNAL_ENABLED | (unset) | Set to `1`, `true`, or `yes` to enable. |
| SIGNAL_RECIPIENT | (unset) | Phone number (e.g. +1234567890) or group ID for signal-cli. |
| SIGNAL_MESSAGE_PREFIX | (unset) | Optional prefix for every alert (e.g. `[Watchtower] `). |

No default secrets; do not commit these in .env to the repo.

## How it works

- **send_alert(title, body)** in `src/alerting/signal_notify.py`: when `SIGNAL_ENABLED` is set and `SIGNAL_RECIPIENT` is set, attempts to send via `signal-cli send RECIPIENT -m "message"`. When disabled or no recipient, no-op or log-only.
- Collector: on uncaught exception (fetch_error), after audit_log, calls `send_alert("Watchtower collector failed", one-line summary)` so you can get notified.

## Plugging in real Signal

### Option 1: signal-cli

1. Install [signal-cli](https://github.com/AsamK/signal-cli) and register/link your number or account.
2. Set in .env:
   - `SIGNAL_ENABLED=1`
   - `SIGNAL_RECIPIENT=+1234567890` (or group ID).
3. The stub runs: `signal-cli send <SIGNAL_RECIPIENT> -m "<message>"`. If your setup requires an account (e.g. `-a ACCOUNT`), edit `src/alerting/signal_notify.py` to add the account argument, or wrap signal-cli in a small script that the stub calls.

### Option 2: Webhook or bot API

If you use a Signal bot API or webhook that accepts HTTP POST:

1. Add env e.g. `SIGNAL_WEBHOOK_URL` in config/settings.py and in this runbook.
2. In `signal_notify.py`, when `SIGNAL_WEBHOOK_URL` is set, POST title/body to that URL instead of (or in addition to) signal-cli.

## Disabling

Leave `SIGNAL_ENABLED` unset or set to `0`/`false`/`no`. Alerts are then no-op; collector still logs to audit and exits 1 on failure.
