# Vendored third-party browser libraries (THIRD_PARTY_NOTICES)

The static dashboard (`scripts/generate_dashboard_html.py` → `exports/dashboard.html`)
used to load its chart libraries from public CDNs (jsDelivr, unpkg, cdnjs). That was a
supply-chain risk flagged in `docs/audit/SECURITY_AUDIT_2026-07-09.md` and meant the
dashboard rendered blank charts without network access.

The libraries below are now vendored here, byte-for-byte unmodified, and **inlined**
into the generated HTML so the dashboard stays a single portable file that works over
`file://` with no network. The generator verifies every sha256 in
[`manifest.json`](manifest.json) before inlining and fails closed on mismatch;
`tests/unit/test_vendor_libs.py` checks the same hashes.

All credit to the upstream authors. Each library keeps its own license file next to it.

| Library | Version | License | Source | Upstream |
|---|---|---|---|---|
| Chart.js | 4.6.1 | MIT | npm `chart.js@4.6.1` (`dist/chart.umd.min.js`; identical bytes to the jsDelivr file previously loaded) | https://github.com/chartjs/Chart.js — © Chart.js Contributors |
| vis-network | 10.1.5 | Apache-2.0 OR MIT (dual) | npm `vis-network@10.1.5` (`standalone/umd/vis-network.min.js`; identical bytes to unpkg) | https://github.com/visjs/vis-network — © Almende B.V., visjs contributors |
| wordcloud2.js | 1.0.2 | MIT | cdnjs `wordcloud2.js/1.0.2/wordcloud2.min.js` (the exact file previously loaded); LICENSE from npm `wordcloud@1.0.2` | https://github.com/timdream/wordcloud2.js — © Timothy Guan-tin Chien and contributors |

The vis-network standalone bundle embeds some of its runtime dependencies, including
core-js (MIT), @egjs/hammerjs (MIT) and keycharm (Apache-2.0 OR MIT), as shipped by
upstream in `vis-network@10.1.5`. All are permissively licensed.

## Files and sha256

| File | sha256 |
|---|---|
| `chart.js-4.6.1/chart.umd.min.js` | `87364cc2b2a76a6684929e7d6b80b18a897794db38400caff1fcf1791c6925d2` |
| `chart.js-4.6.1/LICENSE.md` | `41a84aa2caba645f966a18d9c2056b73e6d3a81d80bc0046bc0011a2634d4cce` |
| `vis-network-10.1.5/vis-network.min.js` | `b427322ad953d70ab75d1b798ebb8349863502f244e02de3e12a4ab7dfeddf2c` |
| `vis-network-10.1.5/LICENSE-MIT` | `1f65085e54c036645082257618db2c7b787e68c3b02485e214ecd09e0834ee8f` |
| `vis-network-10.1.5/LICENSE-APACHE-2.0` | `1509904280a272780fd69c04b858f512cf216f8e3464a0dd98d8f34416feced9` |
| `wordcloud2.js-1.0.2/wordcloud2.min.js` | `0c7ab43960b7422c17fe0a4fdea21de01ca0c3ea1202154d03834785e66df1b1` |
| `wordcloud2.js-1.0.2/LICENSE` | `6084778d56c6807dcb079e111a6322aca2703af29ea4c34eaf01d85ec82a9d7a` |

## Web fonts

The dashboard previously also loaded JetBrains Mono and Source Sans 3 from Google Fonts.
Those fonts are SIL OFL-1.1 (not vendored here); the remote font links were removed and the
CSS falls back to the existing `system-ui` / `ui-monospace` stacks, so no third-party
request is made at all.

## Updating a library

1. Download the new pinned file (prefer the npm tarball) and its LICENSE into a new
   `<name>-<version>/` directory; delete the old directory.
2. Update `manifest.json` (`version`, `script`, `files` with `sha256sum` output) and this file.
3. Run `python -m pytest tests/ -v`.
