# AuditorSpec — moltbook_watchtower release audit

**Date:** 2026-07-09  
**Template:** MiscRepos `.cursor/skills/gui-human-audit/references/AUDITOR_SPEC.md`

---

## AuditorSpec

- **App / repo:** moltbook_watchtower — passive read-only Moltbook network monitor
- **Branch / PR:** `main` @ `b434b7b66b04a307664c7556693714aec301a3bd` (no open PR; release-readiness audit)
- **Environment:** local — generated `exports/dashboard.html` served via ephemeral HTTP (e2e pattern)

- **Base URL:** `http://127.0.0.1:<ephemeral-port>/dashboard.html`
- **Critical routes:** Single surface — static dashboard HTML artifact

- **Top 3 human jobs** (outcomes, not screens):
  1. **Generate** — Run collector + analyzers + `python scripts/generate_dashboard_html.py` against a valid SQLite DB
  2. **Read metrics** — Scan summary stats, findings tables, charts, and network graphs for anomalies
  3. **Export companion data** — Run `python scripts/export_network.py` for CSV/GraphML when graph tools are needed

- **CI / verify targets:**
  - Lint / typecheck: **none** (Python-only; no HTML/CSS linter)
  - Unit / component: `python -m pytest tests/unit/ -v`
  - Integration: `python -m pytest tests/integration/ -v`
  - E2E: `python -m pytest tests/e2e/ -m e2e -v`
  - Full suite (CI): `python -m pytest tests/ -v --tb=short` — **59 tests**
  - Contract (OpenAPI / route index / capabilities): **N/A** — no HTTP API surface
  - A11y / visual: **manual** §7 in `gui-2026-03-26.md`; no axe/Lighthouse in CI
  - Secrets: `.github/workflows/security-gitleaks.yml`

- **Existing audit doc:** [`docs/audit/gui-2026-03-26.md`](gui-2026-03-26.md)

- **Parity / capability docs** (agent-native alignment):
  - No agent-facing REST or MCP API — read-only batch pipeline
  - Embedded `#dashboardData` JSON in generated HTML could feed future tools; no capability manifest today
  - Rationale: product is observability export, not an agent-operable UI

- **Notes:**
  - `exports/`, `data/`, `logs/` are gitignored; e2e uses fixture DB via `DATA_DIR`
  - Dashboard must not be served publicly (`docs/SECURITY.md`)
  - CDN deps: Chart.js, vis-network, wordcloud2, Google Fonts
  - Playwright Chromium required once: `python -m playwright install chromium`

---

## Audit pairing

| Skill | Role in this audit |
|-------|-------------------|
| **gui-human-audit** | Dimension matrix + action items → `gui-2026-03-26.md` §8 |
| **frontend-a2ui** | Applicability memo → expert bundle §A2UI |
| **review-security** | `SECURITY_AUDIT_2026-07-09.md` |
| **browser-review-protocol** | Optional; §7 SR/AT spot-check is manual |
