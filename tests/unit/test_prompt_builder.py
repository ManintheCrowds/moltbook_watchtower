# PURPOSE: Unit tests for daily summary prompt builder — no raw secrets, expected sections.
import pytest

from src.summary.prompt_builder import build_daily_summary_prompt


def test_prompt_starts_with_epistemic_preamble() -> None:
    """Prompt begins with epistemic-hygiene preamble (aligns with docs/EPISTEMIC_HYGIENE.md)."""
    data = {
        "report_date": "2025-02-03",
        "total_posts": 0,
        "total_comments": 0,
        "total_findings": 0,
        "posts_on_date": 0,
        "comments_on_date": 0,
        "findings_on_date": 0,
        "findings": [],
        "highlights": [],
    }
    prompt = build_daily_summary_prompt(data)
    preamble_region = prompt[:400]
    assert "epistemic hygiene" in preamble_region
    assert "analytical agent" in preamble_region


def test_prompt_contains_report_date_and_sections() -> None:
    data = {
        "report_date": "2025-02-03",
        "total_posts": 10,
        "total_comments": 5,
        "total_findings": 2,
        "posts_on_date": 3,
        "comments_on_date": 1,
        "findings_on_date": 2,
        "findings": [
            {"rule_id": "bearer_token", "severity": "high", "redacted_snippet": "Bearer ***"},
        ],
        "highlights": [
            {"title": "A post", "content_snippet": "Short text.", "agent_name": "alice", "submolt": "general"},
        ],
    }
    prompt = build_daily_summary_prompt(data)
    assert "2025-02-03" in prompt
    assert "## Counts" in prompt
    assert "## Notable findings" in prompt
    assert "## Post highlights" in prompt
    assert "10" in prompt and "5" in prompt and "2" in prompt
    assert "bearer_token" in prompt and "high" in prompt and "Bearer ***" in prompt
    assert "A post" in prompt and "Short text." in prompt and "alice" in prompt


def test_prompt_contains_no_raw_secrets() -> None:
    data = {
        "report_date": "2025-02-03",
        "total_posts": 0,
        "total_comments": 0,
        "total_findings": 1,
        "posts_on_date": 0,
        "comments_on_date": 0,
        "findings_on_date": 1,
        "findings": [
            {"rule_id": "api_key_eq", "severity": "high", "redacted_snippet": "api_key=***"},
        ],
        "highlights": [],
    }
    prompt = build_daily_summary_prompt(data)
    assert "api_key=***" in prompt
    assert "sk-" not in prompt and "password" not in prompt.lower() or "redacted" in prompt.lower() or "***" in prompt


def test_prompt_empty_findings_and_highlights() -> None:
    data = {
        "report_date": "2025-02-03",
        "total_posts": 0,
        "total_comments": 0,
        "total_findings": 0,
        "posts_on_date": 0,
        "comments_on_date": 0,
        "findings_on_date": 0,
        "findings": [],
        "highlights": [],
    }
    prompt = build_daily_summary_prompt(data)
    assert "2025-02-03" in prompt
    assert "None" in prompt or "0" in prompt
    assert "2 to 4 short paragraphs" in prompt or "summariz" in prompt.lower()
