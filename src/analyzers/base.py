# PURPOSE: Common finding type for all analyzers; no raw secrets in findings.
# DEPENDENCIES: None
from dataclasses import dataclass
from typing import Optional


@dataclass
class Finding:
    """One analyzer finding: post_id, rule_id, severity, redacted snippet only."""
    post_id: Optional[str]
    comment_id: Optional[str]
    rule_id: str
    severity: str  # e.g. "high", "medium", "low"
    redacted_snippet: Optional[str] = None  # e.g. "Bearer ***" — never the actual secret
