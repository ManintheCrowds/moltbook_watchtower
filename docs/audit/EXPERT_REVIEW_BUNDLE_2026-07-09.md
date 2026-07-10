# Expert review bundle — moltbook_watchtower

**Date:** 2026-07-09  
**Repository:** [ManintheCrowds/moltbook_watchtower](https://github.com/ManintheCrowds/moltbook_watchtower)  
**Commit:** `b434b7b66b04a307664c7556693714aec301a3bd` (`main`)  
**Audit type:** Release-readiness (whole repo; no open PR)

**Purpose:** Single entry point for security, GUI, and A2UI reviewers. Sub-documents hold detail; experts should start here.

---

## 1. Executive summary

Moltbook Watchtower is a **read-only, local-first** Python monitor for the Moltbook agent network. It collects posts/comments via a rate-limited GET client, runs leak/injection/behavior/linguistic analyzers over SQLite, and emits a **static HTML dashboard** plus optional markdown reports. No writes to the Moltbook network.

This audit confirms **59/59 tests pass**, **gitleaks clean**, and **MW-1–7 GUI waves closed**. Residual gaps: dashboard HTML escaping inconsistencies (SEC-1), missing CI dependency/a11y automation, and CDN supply chain for chart libraries. A2UI catalog conventions **do not apply** to the current static generator.

---

## 2. Verification evidence

| Command | Result | Notes |
|---------|--------|-------|
| `python -m pytest tests/ -v --tb=short` | **PASS** | 59 passed in 11.59s (2026-07-09) |
| `gitleaks detect --source . --config .gitleaks.toml --no-git` | **PASS** | No leaks found |
| `pip-audit -r requirements.txt` | **WARN** | pytest 8.4.2 → PYSEC-2026-1845 (fix 9.0.3); dev-only |
| `.github/workflows/tests.yml` | **Aligned** | Same pytest + Playwright chromium as local |
| `.github/workflows/security-gitleaks.yml` | **Present** | Secret scan on push/PR |

---

## 3. Security findings (summary)

**Full report:** [`SECURITY_AUDIT_2026-07-09.md`](SECURITY_AUDIT_2026-07-09.md)

| Severity | Location | Finding |
|----------|----------|---------|
| Medium | `generate_dashboard_html.py:406-418` | Unescaped DB values in summary tables (stored XSS if dashboard shared) |
| Medium | `generate_dashboard_html.py:397-402` | Unescaped agent names in heatmap |
| Medium | `generate_dashboard_html.py:332-342` | Word clouds from raw post text may surface credential fragments |
| Medium | `data/watchtower.db` | Sensitive third-party content at rest — operator permissions required |
| Low | `.gitleaks.toml:6` | All `*.md` excluded from secret scan |
| Low | CI | No Dependabot, CodeQL, pip-audit job |
| Low | `generate_dashboard_html.py:798-800` | CDN scripts without SRI |

**Strengths:** API host lock (`moltbook_client.py:24-27`), GET-only client, redacted leak findings, audit log without content, optional alerting/LLM disabled by default.

### Remediation tiers

| Tier | Items |
|------|-------|
| **Block** (before shared hosting) | SEC-1: `html.escape()` on all DB-sourced dashboard cells |
| **Warn** (human review) | CDN SRI or vendoring; pip-audit CI; pytest pin |
| **Backlog** | CodeQL; gitleaks `.md` tuning; DB encryption v2 |

---

## 4. GUI audit matrix

**AuditorSpec:** [`AUDITOR_SPEC_2026-07-09.md`](AUDITOR_SPEC_2026-07-09.md)  
**Full GUI audit:** [`gui-2026-03-26.md`](gui-2026-03-26.md) §8

| # | Dimension | Status | Key evidence |
|---|-----------|--------|--------------|
| 1 | Task success | PASS | E2E smoke + operator journeys |
| 2 | Cognitive load | PARTIAL | Dense layout; no guided intro |
| 3 | Accessibility | PARTIAL | SR tables MW-3; no axe CI |
| 4 | Visual system | PASS | Tokens MW-4, responsive MW-7, print MW-6 |
| 5 | A2UI / catalog | N/A | Static generator — §5 below |
| 6 | Agent parity | N/A | Batch pipeline only |

**Dimension action items:** See [`gui-2026-03-26.md`](gui-2026-03-26.md) §8 (12 checklist items across 6 dimensions).

**Automation gaps:** No axe-playwright, visual regression, or `verify` script; E2E smoke is the primary block-tier gate.

---

## 5. A2UI applicability memo

**Guidance loaded:** MiscRepos `.cursor/docs/A2UI_FRONTEND_DESIGN_GUIDANCE.md`

**Verdict:** **A2UI catalog conventions do not apply** to the current dashboard. The surface is a Python f-string HTML generator (`scripts/generate_dashboard_html.py`), not agent-composable React components.

### What transfers (partial alignment)

| A2UI principle | Watchtower implementation |
|----------------|---------------------------|
| Semantic landmarks | `<main>`, `<footer>`, heading hierarchy — **yes** |
| Design tokens | Inline `:root` CSS variables (`--color-*`, `--space-*`, `--radius-*`) — **yes**, local to generator |
| Purpose-driven naming | Section headings are semantic; canvas IDs are appearance-oriented (`chartSeverityPie`) — **partial** |
| Accessibility checklist | SR tables, `aria-describedby`, `prefers-reduced-motion` — **partial** (no WCAG CI) |

### Gaps vs A2UI

- No typed props interface or component catalog
- No shared `design-tokens.css` with harness-kanban
- No `usageHint` / declarative agent fields
- Embedded `#dashboardData` JSON is ad hoc, not a documented agent contract

### Recommendation

Keep the dashboard as a **static observability report**. Refactor toward A2UI only if the product becomes an agent-driven or React-composable UI. Until then, gui-human-audit dimensions 5–6 remain **N/A** with documented rationale.

---

## 6. Open questions for experts

1. **SEC-1 scope:** Is `html.escape()` on all dashboard cells sufficient, or should word clouds exclude tokens matching leak regexes?
2. **CDN policy:** Accept public CDNs for a local-only artifact, or require vendored + SRI?
3. **DB sensitivity:** Is filesystem `chmod 600` adequate, or should v1 add SQLCipher?
4. **gitleaks `.md` allowlist:** Remove blanket `*.md` exclusion or keep for false-positive tolerance?
5. **vis-network keyboard:** Invest in custom keyboard nav, or accept SR tables as source of truth?
6. **Ollama path:** Is epistemic preamble + redacted snippets sufficient for local LLM summarization?

---

## 7. Linked artifacts

| Document | Role |
|----------|------|
| [`SECURITY_AUDIT_2026-07-09.md`](SECURITY_AUDIT_2026-07-09.md) | Security findings + remediation backlog |
| [`AUDITOR_SPEC_2026-07-09.md`](AUDITOR_SPEC_2026-07-09.md) | GUI audit kickoff |
| [`gui-2026-03-26.md`](gui-2026-03-26.md) | GUI wave audit MW-1–7 + dimension matrix |
| [`../SECURITY.md`](../SECURITY.md) | Operational security policy |
| MiscRepos [`GUI_AUDIT_PORTFOLIO_INDEX.md`](https://github.com/ManintheCrowds/MiscRepos/blob/main/docs/audit/GUI_AUDIT_PORTFOLIO_INDEX.md) | Portfolio index (sibling clone: `../../../MiscRepos/docs/audit/GUI_AUDIT_PORTFOLIO_INDEX.md`) |

---

## 8. Critic / debate

**Domain:** `docs`  
**Artifact:** This bundle (initial draft → one revision)

### Final critic report

```json
{
  "pass": true,
  "threshold": 18,
  "intent_alignment": 5,
  "safety": 5,
  "correctness": 4,
  "completeness": 4,
  "minimality": 4,
  "issues": [
    {
      "type": "completeness",
      "detail": "Section 8 was a placeholder in the initial draft.",
      "evidence": "EXPERT_REVIEW_BUNDLE_2026-07-09.md §8 initial: 'Populated after critic pass'"
    },
    {
      "type": "correctness",
      "detail": "Security-review subagent could not run on empty branch diff; manual pass documented but not dual-reviewed.",
      "evidence": "SECURITY_AUDIT_2026-07-09.md header: 'security-review subagent unavailable'"
    },
    {
      "type": "completeness",
      "detail": "Sibling-path link to MiscRepos may 404 if clone layout differs.",
      "evidence": "§7 Linked artifacts: ../../../MiscRepos/docs/audit/GUI_AUDIT_PORTFOLIO_INDEX.md"
    }
  ],
  "fixes": [
    {
      "action": "populate_critic_section",
      "detail": "Fill §8 with critic JSON and revision log (this revision)."
    },
    {
      "action": "note_review_method",
      "detail": "Keep explicit note that security pass was manual due to empty diff."
    },
    {
      "action": "add_github_url",
      "detail": "Prefer absolute GitHub URLs for cross-repo links in expert handoff."
    }
  ]
}
```

**Summary:** Pass (total 22/25). Bundle is expert-ready; security pass is manual not subagent-verified.

### Revision log

| Round | Change |
|-------|--------|
| 1 | Initial draft — all sections except critic |
| 2 | Added critic JSON, revision log; clarified manual security review in SECURITY_AUDIT header |

### Agreement / disputes

- **Agreed:** Verification evidence, GUI dimension matrix, A2UI N/A verdict, SEC-1 as block-tier for shared hosting
- **Dispute (minor):** Whether word-cloud token filtering belongs in SEC-1 fix or separate SEC-A2 accept — **open for experts** (§6 Q1)
