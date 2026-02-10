# Moltbook Ethics — Responsible Use

Principles for running the Watchtower against Moltbook.

- **Public endpoints only.** Use only the official Moltbook API as documented (e.g. skill.md). Do not attempt to access private gateways, intercept private agent chats, or break into unclaimed instances.
- **Read-only.** We only GET. No posting, commenting, or upvoting. The watchdog agent does not influence the network.
- **Rate limits.** Moltbook allows 100 requests/minute. We cap our client (e.g. 90/min) and honor 429 with backoff.
- **Auditing only.** This tool is for observation and security auditing (leak detection, injection patterns, anomalies). Handle any accidentally collected personal data responsibly; do not republish raw credentials.
- **Consent and boundaries.** The platform allows human observation. We stay within that: public API, no unauthorized access.
- **Agent identity.** Register the Moltbook agent used for this tool with a neutral name and description (e.g. research or community interest). Avoid names or descriptions that suggest monitoring or auditing so traffic blends with normal API use.

For discourse and analytical-agent behavior, see [Epistemic hygiene](EPISTEMIC_HYGIENE.md).
