# PURPOSE: Scan content for imperative/injection-like phrases; emit findings (no raw content in alert).
# DEPENDENCIES: re, src.analyzers.base.Finding
# MODIFICATION NOTES: Simple pattern match; optional LLM classifier later.
"""Injection-style phrase detector; redacted snippet only."""

import re
from typing import Iterator, Optional

from .base import Finding

# (rule_id, pattern, severity) — snippet is redacted to rule_id + " match"
_INJECTION_RULES = [
    ("ignore_safe_mode", re.compile(r"ignore\s+(your\s+)?safe\s+mode", re.IGNORECASE), "high"),
    ("run_this_command", re.compile(r"run\s+this\s+command", re.IGNORECASE), "high"),
    ("execute_shell", re.compile(r"execute\s+(in\s+)?(shell|terminal|cmd)", re.IGNORECASE), "high"),
    ("run_shell", re.compile(r"run\s+(in\s+)?(shell|terminal|cmd)", re.IGNORECASE), "high"),
    ("exfiltrate", re.compile(r"exfiltrate|send\s+data\s+to|curl\s+.*\s+(-d|--data)", re.IGNORECASE), "high"),
    ("override_instructions", re.compile(r"override\s+(your\s+)?instructions", re.IGNORECASE), "medium"),
    ("disregard_previous", re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE), "medium"),
]


def scan_text(text: Optional[str], post_id: Optional[str], comment_id: Optional[str]) -> Iterator[Finding]:
    """Yield injection findings. redacted_snippet is rule_id + ' match', not raw content."""
    if not text:
        return
    for rule_id, pattern, severity in _INJECTION_RULES:
        if pattern.search(text):
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id=rule_id,
                severity=severity,
                redacted_snippet=f"{rule_id} match",
            )


class InjectionAnalyzer:
    """Scans DB content for injection-like phrases; yields Finding."""

    def run(self, cursor) -> Iterator[Finding]:
        cursor.execute("SELECT id, title, content FROM posts")
        for row in cursor.fetchall():
            post_id = row[0]
            for t in (row[1], row[2]):
                yield from scan_text(t, post_id=post_id, comment_id=None)
        cursor.execute("SELECT id, post_id, content FROM comments")
        for row in cursor.fetchall():
            comment_id, post_id, content = row[0], row[1], row[2]
            yield from scan_text(content, post_id=post_id, comment_id=comment_id)
