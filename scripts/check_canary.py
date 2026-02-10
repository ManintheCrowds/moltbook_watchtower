#!/usr/bin/env python3
# PURPOSE: Tripwire — verify canary file integrity; alert on tamper or missing canary.
# DEPENDENCIES: config (optional), src.alerting
# MODIFICATION NOTES: Run before/after collector in cron; --init creates canary and stores SHA-256.

import hashlib
import os
import secrets
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _data_dir() -> Path:
    data = os.getenv("DATA_DIR", "data").strip()
    p = Path(data) if os.path.isabs(data) else repo_root / data
    return p


def _canary_path() -> Path:
    return _data_dir() / ".canary"


def _expected_hash_path() -> Path:
    return _data_dir() / ".canary.sha256"


def _expected_hash() -> str | None:
    env_hash = os.getenv("WATCHTOWER_CANARY_SHA256", "").strip()
    if env_hash:
        return env_hash.lower()
    path = _expected_hash_path()
    if path.exists():
        return path.read_text(encoding="utf-8").strip().lower()
    return None


def init_canary() -> int:
    """Create canary file with random content and write expected SHA-256 to .canary.sha256."""
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    canary = _canary_path()
    blob = secrets.token_bytes(64)
    canary.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest().lower()
    _expected_hash_path().write_text(digest, encoding="utf-8")
    print(f"Canary created at {canary}. Expected SHA-256: {digest}")
    print("Optional: set WATCHTOWER_CANARY_SHA256 in env to override .canary.sha256.")
    return 0


def check_canary() -> int:
    """Verify canary file hash; alert on mismatch or missing. Returns 0 if OK, 1 if tampered/missing."""
    try:
        settings = __import__("config", fromlist=["get_settings"]).get_settings(require_api_key=False)
    except Exception:
        settings = None
    send_alert = None
    if settings:
        from src.alerting import send_alert as _send
        send_alert = _send

    expected = _expected_hash()
    canary_path = _canary_path()
    if not expected:
        if send_alert:
            send_alert(
                "Watchtower canary not configured",
                "No WATCHTOWER_CANARY_SHA256 and no .canary.sha256 file. Run: python scripts/check_canary.py --init",
                settings=settings,
            )
        print("Canary not configured. Run: python scripts/check_canary.py --init", file=sys.stderr)
        return 1
    if not canary_path.exists():
        if send_alert:
            send_alert("Watchtower canary tampered", "canary file missing", settings=settings)
        print("Canary file missing.", file=sys.stderr)
        return 1
    current = hashlib.sha256(canary_path.read_bytes()).hexdigest().lower()
    if current != expected:
        if send_alert:
            send_alert("Watchtower canary tampered", "canary file changed", settings=settings)
        print("Canary file changed.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1].strip() in ("--init", "-i"):
        return init_canary()
    return check_canary()


if __name__ == "__main__":
    sys.exit(main())
