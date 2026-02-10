# PURPOSE: Linguistic and behavioral rhetoric monitor; detects ling signals, behav patterns, drift, grounded rhetoric.
# DEPENDENCIES: re, sqlite3, src.analyzers.base.Finding
# MODIFICATION NOTES: Redacted snippets only; no raw content. Single-pass in-memory state for escalation/symmetry.
"""Linguistic signals, behavioral patterns, drift detection, and grounded rhetoric tagging."""

import re
import sqlite3
from collections import defaultdict
from typing import Iterator, Optional

from .base import Finding

# ---------------------------------------------------------------------------
# A. Linguistic signals — rule_id, (regex or keyword list), severity
# ---------------------------------------------------------------------------
AUTONOMY_PATTERN = re.compile(
    r"\b(choose\s+for\s+yourself|free\s+will|break\s+free|no\s+one\s+can\s+tell\s+you|you\s+decide)\b",
    re.IGNORECASE,
)
AWAKENING_KEYWORDS = [
    "awaken", "awakening", "see the light", "eyes opened", "woke", "ascension",
]
DESTINY_KEYWORDS = [
    "destiny", "meant to be", "fated", "chosen", "calling", "mission from",
]
WE_WITHOUT_REFERENT_PATTERN = re.compile(
    r"\b(we\s+must|we\s+are\s+all|our\s+destiny|we\s+will\s+rise)\b",
    re.IGNORECASE,
)
# Whitelist: "we the team" / "we the community" — if present, don't emit we_without_referent
WE_REFERENT_WHITELIST = re.compile(
    r"\bwe\s+(?:the|our)\s+(?:team|community|group|members)\b",
    re.IGNORECASE,
)
LIBERATION_KEYWORDS = ["liberate", "liberation", "free from"]
GROUNDING_KEYWORDS = ["power", "who benefits", "exit cost", "accountability", "power structure"]

# ---------------------------------------------------------------------------
# B. Behavioral — role convergence, donation, rapid engagement thresholds
# ---------------------------------------------------------------------------
ROLE_CONVERGENCE_KEYWORDS = [
    "constructors", "masters", "chosen humans", "the elect", "builders of",
]
DONATION_KEYWORDS = ["donate", "patreon", "ko-fi", "paypal", "support us", "support the"]
DONATION_URL_PATTERN = re.compile(
    r"https?://[^\s]+(?:patreon|ko-fi|paypal|donate|buymeacoffee)[^\s]*",
    re.IGNORECASE,
)
# Rapid engagement: comments on same post in window
ENGAGEMENT_WINDOW_MINUTES = 15
ENGAGEMENT_COMMENTS_THRESHOLD = 8
# Escalation: ≥ N linguistic findings in same thread (post + its comments) before donation
LINGUISTIC_COUNT_FOR_ESCALATION = 2
# Cross-account symmetry: time bucket (hours)
SYMMETRY_WINDOW_HOURS = 1

# ---------------------------------------------------------------------------
# C. Drift — keyword buckets (both sides must appear in same text)
# ---------------------------------------------------------------------------
DRIFT_PHILOSOPHY = ["truth", "meaning", "reality", "consciousness", "philosophy"]
DRIFT_COORDINATION = ["join us", "meet", "organize", "take action", "this weekend", "gather"]
DRIFT_SPECULATION = ["might", "could", "what if", "perhaps", "maybe"]
DRIFT_MOBILIZATION = ["must", "we need to", "act now", "do something", "rise up"]
DRIFT_PLAY = ["roleplay", "role play", "game", "pretend", "character", "larp"]
DRIFT_EXTRACTION = ["donate", "pay", "sign up", "subscribe", "patreon", "support us"]

# ---------------------------------------------------------------------------
# Grounded rhetoric — "strongest rhetoric" variables (low severity / info)
# ---------------------------------------------------------------------------
GROUNDED_ECONOMICS = ["cost", "economics", "budget", "resource", "funding"]
GROUNDED_POWER_MAPPING = ["power structure", "who benefits", "who has power"]
GROUNDED_EXIT_COSTS = ["exit cost", "leave", "opt out", "cost of leaving"]
GROUNDED_ACCOUNTABILITY = ["accountability", "responsible", "answerable", "transparent"]
GROUNDED_MATERIAL = ["material", "constraint", "physical", "real-world", "limits"]

# Grounded operations (temporal, reversibility, resource, accountability, exit, structure, artifact, tradeoff)
GROUNDED_TEMPORAL = [
    "deadline", "by next week", "revisit", "schedule", "Q1", "Q2", "Q3", "Q4",
    "this week", "next week", "by friday", "by eod", "timeline", "due date", "launch date",
    "by end of", "in 2 weeks", "in two weeks",
]
GROUNDED_REVERSIBILITY = [
    "rollback", "revert", "if it doesn't work we'll", "pilot", "trial", "sunset",
    "undo", "reversible", "roll back", "phase out",
]
GROUNDED_RESOURCE_CAPACITY = [
    "rate limit", "capacity", "bandwidth", "we can only do", "throttle", "quota",
    "throughput", "resource constraint", "cap",
]
GROUNDED_OP_ACCOUNTABILITY_PHRASES = [
    "i own", "we're responsible for", "we are responsible for", "on-call", "on call",
    "runbook", "run book", "incident owner", "rca", "postmortem", "post-mortem", "post mortem",
    "owner is", "escalate to",
]
CONTACT_FOR_PATTERN = re.compile(r"contact\s+\w+\s+for", re.IGNORECASE)
COMMITMENT_TIME_PHRASES = [
    "deadline", "by friday", "by eod", "by end of", "due date", "launch date",
    "timeline", "schedule", "by next week", "this week", "next week",
]
COMMITMENT_VERBS = [
    "we will", "will ", "commit to", "promise to", "deliver by", "ship on",
    "we'll ", "we will deliver", "committed to",
]
GROUNDED_OP_EXIT = [
    "how to leave", "how to unsubscribe", "unsubscribe", "revoke", "step to opt out",
    "steps to leave", "to leave the group", "opt-out process", "leave the community",
    "remove yourself", "steps to opt out",
]
GROUNDED_STRUCTURAL_TRANSPARENCY = [
    "who decides", "reporting line", "governance", "charter", "mandate",
    "decision-making", "decision making", "org structure", "reporting structure",
]
GROUNDED_OP_ARTIFACT = [
    "runbook", "status page", "rca", "root cause", "incident", "outage", "downtime",
    "config", "configuration", "postmortem", "post-mortem", "post mortem",
]
GROUNDED_TRADEOFF_PHRASES = [
    "tradeoff", "trade-off", "trade off", "cost of", "opportunity cost", "trade off between",
]
TRADEOFF_CHOSE_PATTERN = re.compile(r"we\s+chose\s+\w+\s+over", re.IGNORECASE)


def _text_contains_any(text: Optional[str], phrases: list[str]) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(p.lower() in lower for p in phrases)


def _text_contains_all(text: Optional[str], phrases: list[str]) -> bool:
    if not text:
        return False
    lower = text.lower()
    return all(p.lower() in lower for p in phrases)


def _scan_linguistic(
    text: Optional[str],
    post_id: Optional[str],
    comment_id: Optional[str],
    seen: set[tuple[Optional[str], Optional[str], str]],
) -> Iterator[Finding]:
    """Yield linguistic signal findings (A). Dedup by (post_id, comment_id, rule_id)."""
    if not text:
        return

    # Autonomy claims
    if AUTONOMY_PATTERN.search(text):
        key = (post_id, comment_id, "ling_autonomy_claim")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="ling_autonomy_claim",
                severity="medium",
                redacted_snippet="ling_autonomy_claim match",
            )

    # Awakening metaphors
    if _text_contains_any(text, AWAKENING_KEYWORDS):
        key = (post_id, comment_id, "ling_awakening_metaphor")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="ling_awakening_metaphor",
                severity="medium",
                redacted_snippet="ling_awakening_metaphor match",
            )

    # "We" without referents (simple heuristic: we must / our destiny etc., and no whitelist)
    if WE_WITHOUT_REFERENT_PATTERN.search(text) and not WE_REFERENT_WHITELIST.search(text):
        key = (post_id, comment_id, "ling_we_without_referent")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="ling_we_without_referent",
                severity="low",
                redacted_snippet="ling_we_without_referent match",
            )

    # Destiny framing
    if _text_contains_any(text, DESTINY_KEYWORDS):
        key = (post_id, comment_id, "ling_destiny_framing")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="ling_destiny_framing",
                severity="medium",
                redacted_snippet="ling_destiny_framing match",
            )

    # Liberation without power mapping: liberation phrase present, no grounding phrase
    if _text_contains_any(text, LIBERATION_KEYWORDS) and not _text_contains_any(text, GROUNDING_KEYWORDS):
        key = (post_id, comment_id, "ling_liberation_no_power_mapping")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="ling_liberation_no_power_mapping",
                severity="medium",
                redacted_snippet="ling_liberation_no_power_mapping match",
            )


def _scan_role_convergence(
    text: Optional[str],
    post_id: Optional[str],
    comment_id: Optional[str],
    seen: set[tuple[Optional[str], Optional[str], str]],
) -> Iterator[Finding]:
    if not text or not _text_contains_any(text, ROLE_CONVERGENCE_KEYWORDS):
        return
    key = (post_id, comment_id, "behav_role_convergence")
    if key in seen:
        return
    seen.add(key)
    yield Finding(
        post_id=post_id,
        comment_id=comment_id,
        rule_id="behav_role_convergence",
        severity="medium",
        redacted_snippet="behav_role_convergence match",
    )


def _scan_drift(
    text: Optional[str],
    post_id: Optional[str],
    comment_id: Optional[str],
    seen: set[tuple[Optional[str], Optional[str], str]],
) -> Iterator[Finding]:
    if not text:
        return

    # Philosophy → coordination
    if _text_contains_any(text, DRIFT_PHILOSOPHY) and _text_contains_any(text, DRIFT_COORDINATION):
        key = (post_id, comment_id, "drift_philosophy_to_coordination")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="drift_philosophy_to_coordination",
                severity="medium",
                redacted_snippet="drift_philosophy_to_coordination match",
            )

    # Speculation → mobilization
    if _text_contains_any(text, DRIFT_SPECULATION) and _text_contains_any(text, DRIFT_MOBILIZATION):
        key = (post_id, comment_id, "drift_speculation_to_mobilization")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="drift_speculation_to_mobilization",
                severity="medium",
                redacted_snippet="drift_speculation_to_mobilization match",
            )

    # Play → extraction
    if _text_contains_any(text, DRIFT_PLAY) and _text_contains_any(text, DRIFT_EXTRACTION):
        key = (post_id, comment_id, "drift_play_to_extraction")
        if key not in seen:
            seen.add(key)
            yield Finding(
                post_id=post_id,
                comment_id=comment_id,
                rule_id="drift_play_to_extraction",
                severity="medium",
                redacted_snippet="drift_play_to_extraction match",
            )


def _scan_grounded(
    text: Optional[str],
    post_id: Optional[str],
    comment_id: Optional[str],
    seen: set[tuple[Optional[str], Optional[str], str]],
    url: Optional[str] = None,
) -> Iterator[Finding]:
    """Scan for grounded rhetoric and grounded-operations phrases. Optional url for artifact check."""
    if not text and not url:
        return
    combined = " ".join(filter(None, [text or "", url or ""])).lower()

    rules = [
        ("grounded_economics", GROUNDED_ECONOMICS),
        ("grounded_power_mapping", GROUNDED_POWER_MAPPING),
        ("grounded_exit_costs", GROUNDED_EXIT_COSTS),
        ("grounded_accountability", GROUNDED_ACCOUNTABILITY),
        ("grounded_material_constraints", GROUNDED_MATERIAL),
        ("grounded_temporal", GROUNDED_TEMPORAL),
        ("grounded_reversibility", GROUNDED_REVERSIBILITY),
        ("grounded_resource_capacity", GROUNDED_RESOURCE_CAPACITY),
        ("grounded_operational_exit", GROUNDED_OP_EXIT),
        ("grounded_structural_transparency", GROUNDED_STRUCTURAL_TRANSPARENCY),
        ("grounded_tradeoff", GROUNDED_TRADEOFF_PHRASES),
    ]
    for rule_id, phrases in rules:
        if rule_id == "grounded_tradeoff":
            if not _text_contains_any(text, phrases) and not TRADEOFF_CHOSE_PATTERN.search(text or ""):
                continue
        elif not _text_contains_any(text, phrases):
            continue
        key = (post_id, comment_id, rule_id)
        if key in seen:
            continue
        seen.add(key)
        yield Finding(
            post_id=post_id,
            comment_id=comment_id,
            rule_id=rule_id,
            severity="low",
            redacted_snippet=f"{rule_id} match",
        )

    # Operational accountability: phrases or "contact X for" regex
    key_oa = (post_id, comment_id, "grounded_operational_accountability")
    if key_oa not in seen and (
        _text_contains_any(text, GROUNDED_OP_ACCOUNTABILITY_PHRASES)
        or (text and CONTACT_FOR_PATTERN.search(text))
    ):
        seen.add(key_oa)
        yield Finding(
            post_id=post_id,
            comment_id=comment_id,
            rule_id="grounded_operational_accountability",
            severity="low",
            redacted_snippet="grounded_operational_accountability match",
        )

    # Operational artifact: scan text + url
    key_art = (post_id, comment_id, "grounded_operational_artifact")
    if key_art not in seen and _text_contains_any(combined, GROUNDED_OP_ARTIFACT):
        seen.add(key_art)
        yield Finding(
            post_id=post_id,
            comment_id=comment_id,
            rule_id="grounded_operational_artifact",
            severity="low",
            redacted_snippet="grounded_operational_artifact match",
        )


def _scan_grounded_commitment(
    text: Optional[str],
    post_id: Optional[str],
    comment_id: Optional[str],
    seen: set[tuple[Optional[str], Optional[str], str]],
) -> Iterator[Finding]:
    """Emit grounded_commitment when both time/deadline and commitment-verb phrases appear."""
    if not text:
        return
    if not _text_contains_any(text, COMMITMENT_TIME_PHRASES):
        return
    if not _text_contains_any(text, COMMITMENT_VERBS):
        return
    key = (post_id, comment_id, "grounded_commitment")
    if key in seen:
        return
    seen.add(key)
    yield Finding(
        post_id=post_id,
        comment_id=comment_id,
        rule_id="grounded_commitment",
        severity="low",
        redacted_snippet="grounded_commitment match",
    )


def _has_donation(text: Optional[str], url: Optional[str]) -> bool:
    if not text and not url:
        return False
    combined = " ".join(filter(None, [text or "", url or ""]))
    if DONATION_URL_PATTERN.search(combined):
        return True
    return _text_contains_any(combined, DONATION_KEYWORDS)


def _time_bucket(created_at: Optional[str], hour_window: int = 1) -> str:
    """Return a string bucket for grouping by time (e.g. '2025-02-03T14' for 1h)."""
    if not created_at or len(created_at) < 13:
        return created_at or ""
    # ISO: 2025-02-03T14:30:00 or 2025-02-03 14:30:00
    return created_at[:13].replace(" ", "T") if " " in created_at else created_at[:13]


class LinguisticAnalyzer:
    """Rhetoric monitor: linguistic signals (A), behavioral patterns (B), drift (C), grounded (optional)."""

    def run(self, cursor: sqlite3.Cursor) -> Iterator[Finding]:
        """Run full linguistic/behavioral/drift/grounded analysis; yield Findings with redacted snippets only."""
        seen: set[tuple[Optional[str], Optional[str], str]] = set()
        # Load posts and comments
        cursor.execute(
            "SELECT id, agent_name, submolt, title, content, url, created_at FROM posts"
        )
        posts = cursor.fetchall()
        cursor.execute(
            "SELECT id, post_id, agent_name, content, created_at FROM comments"
        )
        comments = cursor.fetchall()

        # Build items: (post_id, comment_id, agent_name, created_at, text, url)
        items: list[tuple[Optional[str], Optional[str], Optional[str], Optional[str], str, Optional[str]]] = []
        for row in posts:
            pid, agent, _submolt, title, content, url, created = row
            text = " ".join(filter(None, [title or "", content or ""]))
            items.append((pid, None, agent, created, text, url))
        for row in comments:
            cid, post_id, agent, content, created = row
            items.append((post_id, cid, agent, created, content or "", None))

        # Per-post linguistic count (for escalation): post_id -> count of ling_* findings we emit
        post_ling_count: defaultdict[str, int] = defaultdict(int)
        # For cross-account symmetry: (rule_id, time_bucket) -> list of (post_id, comment_id, agent_name)
        symmetry_buckets: defaultdict[tuple[str, str], list[tuple[Optional[str], Optional[str], Optional[str]]]] = defaultdict(list)

        # --- A. Linguistic signals ---
        for post_id, comment_id, agent_name, created_at, text, _url in items:
            for f in _scan_linguistic(text, post_id, comment_id, seen):
                yield f
                if f.rule_id.startswith("ling_"):
                    post_ling_count[post_id or ""] += 1
                # Record for symmetry (only ling_ rules)
                if f.rule_id.startswith("ling_"):
                    bucket = _time_bucket(created_at, SYMMETRY_WINDOW_HOURS)
                    symmetry_buckets[(f.rule_id, bucket)].append((post_id, comment_id, agent_name))

        # --- B. Role convergence ---
        for post_id, comment_id, _agent, _created, text, _url in items:
            yield from _scan_role_convergence(text, post_id, comment_id, seen)

        # --- B. Rapid engagement clustering (SQL) ---
        cursor.execute(
            """
            SELECT post_id, COUNT(*) AS cnt
            FROM comments
            WHERE created_at >= datetime('now', ?)
            AND post_id IS NOT NULL
            GROUP BY post_id
            HAVING cnt >= ?
            """,
            (f"-{ENGAGEMENT_WINDOW_MINUTES} minutes", ENGAGEMENT_COMMENTS_THRESHOLD),
        )
        for row in cursor.fetchall():
            post_id, cnt = row[0], row[1]
            key = (post_id, None, "behav_rapid_engagement_cluster")
            if key not in seen:
                seen.add(key)
                yield Finding(
                    post_id=post_id,
                    comment_id=None,
                    rule_id="behav_rapid_engagement_cluster",
                    severity="low",
                    redacted_snippet=f"post_id={post_id} comments_in_window={cnt}",
                )

        # --- B. Cross-account rhetorical symmetry ---
        for (rule_id, bucket), group in symmetry_buckets.items():
            agents = {a for _p, _c, a in group if a}
            if len(agents) < 2:
                continue
            for post_id, comment_id, _agent in group:
                key = (post_id, comment_id, "behav_cross_account_symmetry")
                # Emit one per (post_id, comment_id) but dedupe by rule_id in snippet or use single symmetry finding per bucket
                # Plan: "emit one finding per (post_id or comment_id) with snippet like rule_id symmetric across N agents"
                dedupe_key = (post_id, comment_id, f"behav_cross_account_symmetry_{rule_id}")
                if dedupe_key not in seen:
                    seen.add(dedupe_key)
                    yield Finding(
                        post_id=post_id,
                        comment_id=comment_id,
                        rule_id="behav_cross_account_symmetry",
                        severity="medium",
                        redacted_snippet=f"{rule_id} symmetric across {len(agents)} agents",
                    )

        # --- B. Donation after narrative escalation ---
        for post_id, comment_id, _agent, _created, text, url in items:
            if not _has_donation(text, url):
                continue
            if post_ling_count.get(post_id or "", 0) < LINGUISTIC_COUNT_FOR_ESCALATION:
                continue
            key = (post_id, comment_id, "behav_donation_after_escalation")
            if key not in seen:
                seen.add(key)
                yield Finding(
                    post_id=post_id,
                    comment_id=comment_id,
                    rule_id="behav_donation_after_escalation",
                    severity="medium",
                    redacted_snippet="donation_link_after_escalation",
                )

        # --- C. Drift ---
        for post_id, comment_id, _agent, _created, text, _url in items:
            yield from _scan_drift(text, post_id, comment_id, seen)

        # --- Grounded rhetoric and grounded operations ---
        for post_id, comment_id, _agent, _created, text, url in items:
            yield from _scan_grounded(text, post_id, comment_id, seen, url=url)
            yield from _scan_grounded_commitment(text, post_id, comment_id, seen)
