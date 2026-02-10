# Linguistic and Rhetoric Monitor

The **linguistic analyzer** (`LinguisticAnalyzer`) runs with leak, injection, and behavior. It detects rhetoric signals, behavioral patterns, discourse drift, and optional “grounded” rhetoric. All findings use **redacted snippets only** — no raw post or comment content is stored or logged. Observation only; aligned with [MOLTBOOK_ETHICS.md](MOLTBOOK_ETHICS.md).

## Rule ID prefixes

Findings use these prefixes so the dashboard and runbooks can group them:

| Prefix      | Category           | Description |
|------------|--------------------|-------------|
| `ling_*`   | Linguistic signals | Autonomy claims, awakening metaphors, “we” without referents, destiny framing, liberation without power mapping |
| `behav_*`  | Behavioral patterns| Rapid engagement clustering, cross-account rhetorical symmetry, donation-after-escalation, role convergence |
| `drift_*`  | Drift detection   | Philosophy→coordination, speculation→mobilization, play→extraction |
| `grounded_*` | Grounded rhetoric and operations | Economics, power mapping, exit costs, accountability, material constraints; temporal, reversibility, resource, operational accountability/exit/artifact, structural transparency, tradeoff, commitment heuristic (low severity / informational) |

## Rule IDs reference

### A. Linguistic signals (`ling_*`)

- **ling_autonomy_claim** — e.g. “choose for yourself”, “free will”, “break free”, “you decide” (medium).
- **ling_awakening_metaphor** — e.g. “awaken”, “see the light”, “ascension” (medium).
- **ling_we_without_referent** — “we must”, “our destiny” etc. without “we the team/community” (low).
- **ling_destiny_framing** — e.g. “destiny”, “meant to be”, “chosen”, “calling” (medium).
- **ling_liberation_no_power_mapping** — liberation language without grounding (power, who benefits, exit cost, accountability) in same text (medium).

### B. Behavioral patterns (`behav_*`)

- **behav_rapid_engagement_cluster** — many comments on the same post in a short time window (low).
- **behav_cross_account_symmetry** — same linguistic rule fires in the same time window from ≥2 distinct agents (medium).
- **behav_donation_after_escalation** — donation link or phrase appears in a thread that already has ≥N linguistic findings (medium).
- **behav_role_convergence** — e.g. “Constructors”, “masters”, “chosen humans”, “the elect”, “builders of” (medium).

### C. Drift detection (`drift_*`)

- **drift_philosophy_to_coordination** — philosophy keywords + coordination keywords in same text (medium).
- **drift_speculation_to_mobilization** — speculation + mobilization in same text (medium).
- **drift_play_to_extraction** — play/roleplay + extraction/donation in same text (medium).

### Grounded rhetoric and operations (`grounded_*`)

**Original rhetoric (reality-anchoring variables):**

- **grounded_economics**, **grounded_power_mapping**, **grounded_exit_costs**, **grounded_accountability**, **grounded_material_constraints** — content that reintroduces economics, power mapping, exit costs, accountability, or material constraints (low severity).

**Grounded operations (observable in language):**

- **grounded_temporal** — concrete time references: deadline, schedule, Q1–Q4, “by Friday”, “revisit”, timeline, due date, launch date.
- **grounded_reversibility** — rollback, revert, pilot, trial, sunset, undo, reversible, phase out.
- **grounded_resource_capacity** — rate limit, capacity, bandwidth, throttle, quota, throughput, resource constraint.
- **grounded_operational_accountability** — I own, runbook, on-call, incident owner, RCA, postmortem, “contact X for”, escalate to.
- **grounded_commitment** — two-bucket heuristic: time/deadline phrase and commitment verb (“will”, “commit to”, “deliver by”) in same text (testable commitment).
- **grounded_operational_exit** — procedural exit: how to leave, unsubscribe, revoke, steps to opt out, leave the community.
- **grounded_structural_transparency** — who decides, reporting line, governance, charter, mandate, decision-making, org structure.
- **grounded_operational_artifact** — runbook, status page, RCA, incident, outage, config, postmortem (content or URL).
- **grounded_tradeoff** — tradeoff, opportunity cost, “we chose X over Y”, cost of.

## Behavioral ratios

Ratios of **grounded_*** vs **ling_*** / **drift_*** help see which agents or submolts mix grounded language with rhetoric, and how that changes over time.

- **Script:** Run `python scripts/grounded_ratios.py` to generate `exports/grounded_ratios.md` with:
  - Per-agent: distinct items (post or comment) with at least one grounded finding vs rhetoric finding (top 30 by activity).
  - Per-submolt: same (top 20).
  - Trend: findings per day by prefix (grounded / rhetoric / other).
- **Dashboard:** The static dashboard (`scripts/generate_dashboard_html.py`) includes a “Grounded vs rhetoric” section with per-agent and per-submolt tables and a daily trend table. No schema change; uses JOINs of `findings` with `posts` and `comments`.

## Implementation notes

- Rules are regex and keyword lists in `src/analyzers/linguistic.py`. No raw content in snippets.
- Cross-account symmetry and donation-after-escalation use in-memory state from the same run (no extra DB tables).
- The dashboard and reports show findings by `rule_id` and severity; filter by prefix to see ling/behav/drift/grounded separately.
