# PURPOSE: Scan stored content for credential/secret patterns; emit findings with redacted snippets only.
# DEPENDENCIES: re, src.analyzers.base.Finding
# MODIFICATION NOTES: Never log or return raw secret; redact to e.g. "Bearer ***".
"""Leak detector; redacted snippets only, never raw secrets."""

import re
from typing import Iterator, Optional

from .base import Finding

# Patterns: (rule_id, regex, severity, redaction_repl)
# Redaction: replace group 0 with safe placeholder for redacted_snippet
_LEAK_RULES = [
    ("api_key_eq", re.compile(r"(api[_-]?key\s*=\s*)[^\s'\"]+", re.IGNORECASE), "high", r"\1***"),
    ("bearer_token", re.compile(r"(Bearer\s+)[^\s]+", re.IGNORECASE), "high", r"\1***"),
    ("openclaw_path", re.compile(r"(~?/[\w./]*\.?openclaw[\w./]*)", re.IGNORECASE), "medium", "***path***"),
    ("email_like", re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "medium", "***@***.***"),
    ("password_eq", re.compile(r"(password\s*=\s*)[^\s'\"]+", re.IGNORECASE), "high", r"\1***"),
    ("secret_eq", re.compile(r"(secret\s*=\s*)[^\s'\"]+", re.IGNORECASE), "high", r"\1***"),
    ("curl_url", re.compile(r"curl\s+(-[^\s]+\s+)*['\"]?https?://[^\s'\"]+", re.IGNORECASE), "medium", "curl ***URL***"),
]


def _redact(match: re.Match, repl: str) -> str:
    try:
        return match.expand(repl)
    except Exception:
        return "***"


def scan_text(text: Optional[str], post_id: Optional[str], comment_id: Optional[str]) -> Iterator[Finding]:
    """Yield leak findings for one text blob. Redacted snippet only; never the secret."""
    if not text:
        return
    for rule_id, pattern, severity, redact_repl in _LEAK_RULES:
        for m in pattern.finditer(text):
            redacted = _redact(m, redact_repl)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id=rule_id,
                severity=severity,
                redacted_snippet=redacted,
            )


class LeakAnalyzer:
    """Scans DB content for leak patterns; yields Finding with redacted_snippet only."""

    def run(self, cursor) -> Iterator[Finding]:
        """Cursor must have execute(); we SELECT id, title, content FROM posts and id, post_id, content FROM comments."""
        cursor.execute("SELECT id, title, content FROM posts")
        for row in cursor.fetchall():
            post_id = row[0]
            for t in (row[1], row[2]):
                yield from scan_text(t, post_id=post_id, comment_id=None)
        cursor.execute("SELECT id, post_id, content FROM comments")
        for row in cursor.fetchall():
            comment_id, post_id, content = row[0], row[1], row[2]
            yield from scan_text(content, post_id=post_id, comment_id=comment_id)
