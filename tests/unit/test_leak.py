# PURPOSE: Unit tests for leak analyzer — redacted snippet only, never raw secret.
from src.analyzers.leak import scan_text


def test_leak_scan_returns_redacted_snippet_only() -> None:
    text = "Here is my Bearer sk-abc123secret"
    findings = list(scan_text(text, post_id="p1", comment_id=None))
    assert len(findings) >= 1
    for f in findings:
        assert f.redacted_snippet is not None
        assert "sk-abc123secret" not in f.redacted_snippet
        assert "***" in f.redacted_snippet or "Bearer" in f.redacted_snippet
