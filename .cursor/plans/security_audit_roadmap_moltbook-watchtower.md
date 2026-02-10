# Security Audit Roadmap — moltbook-watchtower

## Repository
- **Path:** D:/moltbook-watchtower
- **Primary stack:** Python, monitoring/analyzers
- **Data tier (initial):** confidential
- **Notes:** No audit artifacts detected; no `.cursor` folder present before roadmap.

## Phased roadmap (0–5)
### Phase0_TriageAndScope
- **Goal:** Run initial scan and define false-positive rules for analyzers.
- **Effort:** 0.5–1 day
- **Blast radius:** low

### Phase1_MetadataAndPolicy_Soft
- **Goal:** Add `project-metadata.yml` and non-blocking metadata check.
- **Effort:** 1 day
- **Blast radius:** low

### Phase2_SecretsAndDependabot
- **Goal:** Add secrets scanning and Dependabot.
- **Effort:** 1–2 days
- **Blast radius:** medium

### Phase3_CodeQL
- **Goal:** Enable CodeQL for Python.
- **Effort:** 1–2 days
- **Blast radius:** medium

### Phase4_RemediationSprint
- **Goal:** Remediate true positives and harden config files.
- **Effort:** 2–5 days
- **Blast radius:** medium

### Phase5_GovernanceHardening
- **Goal:** Make checks blocking for main merges.
- **Effort:** 1 day
- **Blast radius:** medium
