# PURPOSE: Unit tests for audit log — payload does not accept content field.
import json
import tempfile
from pathlib import Path

from src.scheduler.audit import audit_log


def test_audit_log_does_not_include_content_in_payload() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "audit.jsonl"
        audit_log(path, "test_event", extra={"count": 1})
        line = path.read_text().strip()
        payload = json.loads(line)
        assert "event" in payload
        assert "content" not in payload
        assert "body" not in payload
