# Security audit — moltbook_watchtower

**Date:** 2026-07-09  
**Scope:** Whole repo on `main` @ `b434b7b66b04a307664c7556693714aec301a3bd`  
**Mode:** Read-only review (no code changes in this audit)  
**Reviewer:** Agent security pass (security-review subagent unavailable — empty branch diff on `main`)

---

## Executive summary

Moltbook Watchtower is a **read-only, local-first** Python monitor with a deliberately narrow egress surface: API keys are restricted to `https://www.moltbook.com`, the client exposes GET-only methods, and analyzers emit **redacted snippets** rather than raw secrets. Audit logging and alerting follow a no-content-in-logs policy. The main residual risks are **sensitive data at rest** (SQLite holds third-party leaked credentials), **inconsistent HTML escaping** in the dashboard generator (stored XSS if the HTML is served to others), **CDN supply chain** for chart libraries, and **CI gaps** (no Dependabot, CodeQL, or scoped `pip-audit`). Optional Ollama summarization and Signal alerting add local subprocess/LLM surfaces that are disabled by default but need operator discipline.

---

## Verification evidence (2026-07-09)

| Check | Result |
|-------|--------|
| `pytest tests/ -v --tb=short` | **PASS** — 60 passed (includes SEC-1 `test_dashboard_escape.py`) |
| `gitleaks detect --no-git` | **PASS** — no leaks found |
| `pip-audit -r requirements.txt` | **WARN** — pytest 8.4.2 → PYSEC-2026-1845 (fix 9.0.3); dev-only dep |

---

## Findings

| Severity | Location | Finding |
|----------|----------|---------|
| Medium | `scripts/generate_dashboard_html.py:406-418` | ~~Several summary tables embed DB values without `html.escape()`~~ **Fixed** in PR `fix/sec-1-dashboard-escape` (`_cell()` helper; `tests/unit/test_dashboard_escape.py`). |
| Medium | `scripts/generate_dashboard_html.py:397-402` | ~~Heatmap unescaped agent~~ **Fixed** same PR. |
| Medium | `scripts/generate_dashboard_html.py:332-342` | Word clouds tokenize **raw post/submolt text** from DB; tokens may include credential fragments not caught by leak rules. Policy says open dashboard locally only — document and consider filtering tokens against leak patterns. |
| Medium | `data/watchtower.db` (operational) | DB stores full post/comment bodies including third-party secrets. Filesystem permissions and backup encryption are operator responsibility (`docs/SECURITY.md` L16-17, L34). |
| Low | `.gitleaks.toml:6` | Allowlist excludes all `*.md` files from secret scanning — pasted keys in docs would not be caught. |
| Low | `.github/workflows/` | CI runs pytest + gitleaks only. No Dependabot, CodeQL, Bandit, or `pip-audit` (roadmap: MiscRepos `plans/security_audit_roadmap_moltbook-watchtower.md`). |
| Low | `requirements.txt` | `pytest` 8.4.2 has known advisory (PYSEC-2026-1845); dev/test dependency only. |
| Low | `scripts/generate_dashboard_html.py:798-800` | Dashboard loads Chart.js, vis-network, wordcloud2 from public CDNs (jsdelivr, unpkg, cdnjs). Supply-chain risk if CDN compromised; SRI hashes not used. |
| Low | `src/alerting/signal_notify.py:39-44` | `subprocess.run(["signal-cli", "send", recipient, "-m", message])` — list form avoids shell injection; `recipient` and `message` are env/operator-controlled. Timeout (10s) present. Risk is alert body echoing operational metadata, not RCE. |
| Info | `src/client/moltbook_client.py:24-27` | Host lock enforced at init; `_get` is GET-only. **Good.** Unit test `test_client_rejects_non_moltbook_base_url` covers evil host. |
| Info | `src/analyzers/leak.py:31-44` | Findings use redacted snippets only. **Good.** |
| Info | `src/scheduler/audit.py:18` | Audit log contract: no post/comment content. **Good.** |
| Info | `src/summary/prompt_builder.py:17-43` | Ollama prompt uses redacted snippets + epistemic preamble. Residual: prompt injection from redacted-but-adversarial snippet text into local LLM. |
| Info | `src/summary/ollama_client.py:21-24` | POST to local Ollama only (operator-configured base URL). Not enabled in default path. |
| Info | `docs/SECURITY.md:35-37` | Formatting glitch — sections run together; minor doc hygiene. |

---

## Remediation backlog

### Fix (recommended before public demo or shared hosting)

| ID | Item | Rationale |
|----|------|-----------|
| SEC-1 | ~~Apply `html.escape()`~~ **Fixed** — branch `fix/sec-1-dashboard-escape`; 60 tests pass with `test_dashboard_escape.py` | Closed stored XSS in summary tables and heatmap |
| SEC-2 | Add SRI or vendor pinned local copies for CDN scripts | Reduce supply-chain risk |
| SEC-3 | Add Dependabot + `pip-audit` CI job (or pin pytest ≥9.0.3) | Close dependency hygiene gap |

### Accept (documented risk, operator-controlled)

| ID | Item | Rationale |
|----|------|-----------|
| SEC-A1 | Sensitive SQLite at rest | Inherent to monitoring mission; mitigated by local-only + permissions |
| SEC-A2 | Word cloud from raw text | Accept if dashboard stays local; document in SECURITY.md |
| SEC-A3 | Optional Ollama / Signal paths | Disabled by default; epistemic hygiene doc exists |

### Defer (backlog / roadmap)

| ID | Item | Rationale |
|----|------|-----------|
| SEC-D1 | CodeQL for Python | Roadmap Phase 3 |
| SEC-D2 | Narrow gitleaks `.md` allowlist | May increase false positives; tune per repo |
| SEC-D3 | DB encryption at rest | v2 if cloud sync added |
| SEC-D4 | vis-network keyboard hardening | Accessibility, not security-critical |

---

## Cross-references

- Policy: [`docs/SECURITY.md`](../SECURITY.md)
- GUI / XSS context: [`docs/audit/gui-2026-03-26.md`](gui-2026-03-26.md) §8
- Expert bundle: [`docs/audit/EXPERT_REVIEW_BUNDLE_2026-07-09.md`](EXPERT_REVIEW_BUNDLE_2026-07-09.md)
