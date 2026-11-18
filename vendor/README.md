# Vendored third-party browser libraries (THIRD_PARTY_NOTICES)

The static dashboard (`scripts/generate_dashboard_html.py` → `exports/dashboard.html`)
used to load its chart libraries from public CDNs (jsDelivr, unpkg, cdnjs) and its
UI fonts from Google Fonts. That was a supply-chain risk flagged in
`docs/audit/SECURITY_AUDIT_2026-07-09.md` and meant the dashboard rendered blank
charts — and fell back to system fonts — without network access.

The libraries and fonts below are now vendored here, byte-for-byte unmodified, and
**inlined** into the generated HTML so the dashboard stays a single portable file
that works over `file://` with no network. The generator verifies every sha256 in
[`manifest.json`](manifest.json) before inlining and fails closed on mismatch;
`tests/unit/test_vendor_libs.py` checks the same hashes. Scripts are inlined as
`<script>` tags; fonts are inlined as `@font-face` rules with `data:font/woff2;base64,…`
URIs. The CSS keeps the existing `system-ui` / `ui-monospace` fallbacks after the
vendored family names.

All credit to the upstream authors. Each library or font keeps its own license file
next to it.

| Library | Version | License | Source | Upstream |
|---|---|---|---|---|
| Chart.js | 4.6.1 | MIT | npm `chart.js@4.6.1` (`dist/chart.umd.min.js`; identical bytes to the jsDelivr file previously loaded) | https://github.com/chartjs/Chart.js — © Chart.js Contributors |
| vis-network | 10.1.5 | Apache-2.0 OR MIT (dual) | npm `vis-network@10.1.5` (`standalone/umd/vis-network.min.js`; identical bytes to unpkg) | https://github.com/visjs/vis-network — © Almende B.V., visjs contributors |
| wordcloud2.js | 1.0.2 | MIT | cdnjs `wordcloud2.js/1.0.2/wordcloud2.min.js` (the exact file previously loaded); LICENSE from npm `wordcloud@1.0.2` | https://github.com/timdream/wordcloud2.js — © Timothy Guan-tin Chien and contributors |
| JetBrains Mono | 2.304 | SIL OFL-1.1 | official release zip `JetBrainsMono-2.304.zip` (`fonts/webfonts/JetBrainsMono-{Medium,SemiBold,Bold}.woff2` and `OFL.txt`) | https://github.com/JetBrains/JetBrainsMono — © The JetBrains Mono Project Authors |
| Source Sans 3 | 3.052 | SIL OFL-1.1 | official release zip `WOFF2-source-sans-3.052R.zip` (`WOFF2/TTF/SourceSans3-{Regular,Semibold,It}.ttf.woff2`); `LICENSE.md` from the `3.052R` tag | https://github.com/adobe-fonts/source-sans — © Adobe, designed by Paul D. Hunt |

The vis-network standalone bundle embeds some of its runtime dependencies, including
core-js (MIT), @egjs/hammerjs (MIT) and keycharm (Apache-2.0 OR MIT), as shipped by
upstream in `vis-network@10.1.5`. All are permissively licensed.

The dashboard previously loaded JetBrains Mono (weights 500, 600, 700) and Source Sans 3
(roman 400 and 600, italic 400) from Google Fonts. Only those weights are vendored, as
official unmodified woff2 files. The generated HTML no longer requests
`fonts.googleapis.com` or `fonts.gstatic.com`.

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
| `jetbrains-mono-2.304/JetBrainsMono-Medium.woff2` | `086c48dfbea9ddaff1320f7e09399b8e2924e88ce67453721255db3bdbb5a353` |
| `jetbrains-mono-2.304/JetBrainsMono-SemiBold.woff2` | `918edad542a1da608fd2ba8daebaff9ac802309103fe760eed465b8b4e47faf1` |
| `jetbrains-mono-2.304/JetBrainsMono-Bold.woff2` | `c503cc5ec5f8b2c7666b7ecda1adf44bd45f2e6579b2eba0fc292150416588a2` |
| `jetbrains-mono-2.304/OFL.txt` | `30f0c136e3c88e422d0791acd97238870f9054a9729bc34cf2ff0d4ed8cac4ad` |
| `source-sans-3.052/SourceSans3-Regular.woff2` | `53492fb3a0def77354f166a55d09b63a10855e91c206c7620a81cf56e97f8ec3` |
| `source-sans-3.052/SourceSans3-Semibold.woff2` | `47b9b661b9f395fe7f0d0e119637fba5c8dad97bde3df60066fd24229c0792f4` |
| `source-sans-3.052/SourceSans3-It.woff2` | `4d80b3b801f4c457f1b4adbd3911d8501338e6d282141663770c38d3a2e97859` |
| `source-sans-3.052/LICENSE.md` | `89ad2c4f66dd29127527493e729c31e731f111cf10faf5774c3db9275ed0c22c` |

## Updating a library or font

1. Download the new pinned file (prefer the npm tarball, or the official GitHub
   release zip for fonts) and its LICENSE into a new `<name>-<version>/` directory;
   delete the old directory. For fonts, keep only the weights the dashboard CSS uses.
2. Update `manifest.json` (`version`, `script` or `faces`, `files` with `sha256sum`
   output) and this file.
3. Run `python -m pytest tests/ -v`.
