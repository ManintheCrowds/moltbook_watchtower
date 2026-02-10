# PURPOSE: Audit log for our actions — endpoint, time, status, count; no raw content.
# DEPENDENCIES: pathlib, json
# MODIFICATION NOTES: Logs to logs/audit.jsonl (gitignored).

import json
from pathlib import Path
from typing import Any, Optional


def audit_log(
    log_path: Path,
    event: str,
    endpoint: Optional[str] = None,
    status: Optional[int] = None,
    record_count: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Append one JSON line to audit log. Do not pass post/comment content."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"event": event}
    if endpoint is not None:
        payload["endpoint"] = endpoint
    if status is not None:
        payload["status"] = status
    if record_count is not None:
        payload["record_count"] = record_count
    if extra:
        payload["extra"] = extra
    from datetime import datetime, timezone
    payload["ts"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(payload) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
