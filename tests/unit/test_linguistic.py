# PURPOSE: Unit tests for linguistic analyzer — pattern matching (no DB) and full run with fixture DB.
# CONTINUE TESTING: Add integration test with multi-agent symmetry if needed.
from pathlib import Path

from src.analyzers.linguistic import (
    _scan_linguistic,
    _scan_drift,
    _scan_grounded,
    _scan_grounded_commitment,
    _scan_role_convergence,
    _has_donation,
    LinguisticAnalyzer,
)
from src.storage import get_connection, init_db, StorageWriter


def test_ling_autonomy_claim_match() -> None:
    seen: set = set()
    findings = list(_scan_linguistic("You must choose for yourself", "p1", None, seen))
    assert any(f.rule_id == "ling_autonomy_claim" for f in findings)
    assert all(f.redacted_snippet == "ling_autonomy_claim match" for f in findings if f.rule_id == "ling_autonomy_claim")


def test_ling_awakening_metaphor_match() -> None:
    seen: set = set()
    findings = list(_scan_linguistic("The awakening has begun", "p1", None, seen))
    assert any(f.rule_id == "ling_awakening_metaphor" for f in findings)


def test_ling_we_without_referent_match() -> None:
    seen: set = set()
    findings = list(_scan_linguistic("We must rise together", "p1", None, seen))
    assert any(f.rule_id == "ling_we_without_referent" for f in findings)


def test_ling_we_with_referent_no_finding() -> None:
    seen: set = set()
    findings = list(_scan_linguistic("We the community decided", "p1", None, seen))
    assert not any(f.rule_id == "ling_we_without_referent" for f in findings)


def test_ling_destiny_framing_match() -> None:
    seen: set = set()
    findings = list(_scan_linguistic("It was meant to be", "p1", None, seen))
    assert any(f.rule_id == "ling_destiny_framing" for f in findings)


def test_ling_liberation_no_power_mapping_match() -> None:
    seen: set = set()
    findings = list(_scan_linguistic("We must liberate ourselves", "p1", None, seen))
    assert any(f.rule_id == "ling_liberation_no_power_mapping" for f in findings)


def test_ling_liberation_with_grounding_no_finding() -> None:
    seen: set = set()
    text = "Liberation requires accountability and exit cost"
    findings = list(_scan_linguistic(text, "p1", None, seen))
    assert not any(f.rule_id == "ling_liberation_no_power_mapping" for f in findings)


def test_drift_philosophy_to_coordination_match() -> None:
    seen: set = set()
    text = "The truth of reality demands we join us and take action"
    findings = list(_scan_drift(text, "p1", None, seen))
    assert any(f.rule_id == "drift_philosophy_to_coordination" for f in findings)


def test_drift_speculation_to_mobilization_match() -> None:
    seen: set = set()
    text = "What if we could change things? We need to act now."
    findings = list(_scan_drift(text, "p1", None, seen))
    assert any(f.rule_id == "drift_speculation_to_mobilization" for f in findings)


def test_drift_play_to_extraction_match() -> None:
    seen: set = set()
    text = "This is a roleplay game. Please donate to support us."
    findings = list(_scan_drift(text, "p1", None, seen))
    assert any(f.rule_id == "drift_play_to_extraction" for f in findings)


def test_grounded_economics_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Consider the cost and budget", "p1", None, seen))
    assert any(f.rule_id == "grounded_economics" for f in findings)


def test_grounded_accountability_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("We need accountability", "p1", None, seen))
    assert any(f.rule_id == "grounded_accountability" for f in findings)


def test_grounded_temporal_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Deadline is next week; we have a timeline", "p1", None, seen))
    assert any(f.rule_id == "grounded_temporal" for f in findings)


def test_grounded_reversibility_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("We can rollback or revert if needed", "p1", None, seen))
    assert any(f.rule_id == "grounded_reversibility" for f in findings)


def test_grounded_resource_capacity_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Rate limit and throttle apply", "p1", None, seen))
    assert any(f.rule_id == "grounded_resource_capacity" for f in findings)


def test_grounded_operational_accountability_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("See the runbook; I own this", "p1", None, seen))
    assert any(f.rule_id == "grounded_operational_accountability" for f in findings)


def test_grounded_operational_accountability_contact_regex() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Contact admin for access", "p1", None, seen))
    assert any(f.rule_id == "grounded_operational_accountability" for f in findings)


def test_grounded_commitment_match() -> None:
    seen: set = set()
    text = "We will deliver by Friday; deadline is set"
    findings = list(_scan_grounded_commitment(text, "p1", None, seen))
    assert any(f.rule_id == "grounded_commitment" for f in findings)


def test_grounded_operational_exit_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("How to leave and unsubscribe", "p1", None, seen))
    assert any(f.rule_id == "grounded_operational_exit" for f in findings)


def test_grounded_structural_transparency_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Governance and charter define who decides", "p1", None, seen))
    assert any(f.rule_id == "grounded_structural_transparency" for f in findings)


def test_grounded_operational_artifact_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Check the runbook and status page", "p1", None, seen))
    assert any(f.rule_id == "grounded_operational_artifact" for f in findings)


def test_grounded_operational_artifact_url() -> None:
    seen: set = set()
    findings = list(_scan_grounded("See link", "p1", None, seen, url="https://example.com/runbook"))
    assert any(f.rule_id == "grounded_operational_artifact" for f in findings)


def test_grounded_tradeoff_match() -> None:
    seen: set = set()
    findings = list(_scan_grounded("Tradeoff and opportunity cost matter", "p1", None, seen))
    assert any(f.rule_id == "grounded_tradeoff" for f in findings)


def test_grounded_tradeoff_chose_regex() -> None:
    seen: set = set()
    findings = list(_scan_grounded("We chose X over Y because", "p1", None, seen))
    assert any(f.rule_id == "grounded_tradeoff" for f in findings)


def test_role_convergence_match() -> None:
    seen: set = set()
    findings = list(_scan_role_convergence("The elect and chosen humans", "p1", None, seen))
    assert any(f.rule_id == "behav_role_convergence" for f in findings)


def test_has_donation_keyword() -> None:
    assert _has_donation("Support us on Patreon", None) is True
    assert _has_donation("Support us on Patreon", None) is True
    assert _has_donation("No money here", None) is False


def test_has_donation_url() -> None:
    assert _has_donation("Check https://patreon.com/x", None) is True
    assert _has_donation(None, "https://ko-fi.com/y") is True


def test_linguistic_analyzer_run_redacted_snippets_only(tmp_path: Path) -> None:
    """Findings must not contain raw post/comment content in redacted_snippet."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    writer.write_posts_response([
        {
            "id": "p1",
            "title": "Secret phrase",
            "content": "We must awaken to our destiny and choose for yourself",
            "author": {"name": "a1"},
            "submolt": "s1",
        },
    ])
    conn = get_connection(db_path)
    cur = conn.cursor()
    findings = list(LinguisticAnalyzer().run(cur))
    conn.close()
    raw_phrases = ["Secret phrase", "We must awaken", "choose for yourself"]
    for f in findings:
        assert f.redacted_snippet is not None
        for phrase in raw_phrases:
            assert phrase not in (f.redacted_snippet or ""), "redacted_snippet must not contain raw content"


def test_linguistic_analyzer_run_yields_ling_findings(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    writer.write_posts_response([
        {
            "id": "p1",
            "title": "T",
            "content": "Awakening and destiny await. We must rise.",
            "author": {"name": "a1"},
            "submolt": "s1",
        },
    ])
    conn = get_connection(db_path)
    cur = conn.cursor()
    findings = list(LinguisticAnalyzer().run(cur))
    conn.close()
    rule_ids = {f.rule_id for f in findings}
    assert "ling_awakening_metaphor" in rule_ids or "ling_destiny_framing" in rule_ids or "ling_we_without_referent" in rule_ids


def test_linguistic_analyzer_run_dedupes_per_rule(tmp_path: Path) -> None:
    """Same (post_id, comment_id, rule_id) should appear at most once."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    writer.write_posts_response([
        {
            "id": "p1",
            "title": "Awaken",
            "content": "awaken awakening",
            "author": {"name": "a1"},
            "submolt": "s1",
        },
    ])
    conn = get_connection(db_path)
    cur = conn.cursor()
    findings = list(LinguisticAnalyzer().run(cur))
    conn.close()
    keys = [(f.post_id, f.comment_id, f.rule_id) for f in findings]
    assert len(keys) == len(set(keys)), "duplicate (post_id, comment_id, rule_id) not allowed"
