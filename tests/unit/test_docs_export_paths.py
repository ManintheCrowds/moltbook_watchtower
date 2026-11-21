# PURPOSE: Guard user-facing docs against stale output paths.
# Every script writes outputs to settings.db_path.parent / "exports" (i.e. <DATA_DIR>/exports/,
# default data/exports/), not to a repo-root exports/ folder. Docs must say so.
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
USER_DOCS = [REPO / "README.md", REPO / "ROADMAP.md", *sorted((REPO / "docs").glob("*.md")), *sorted((REPO / "docs" / "runbooks").glob("*.md"))]
OUTPUT_SCRIPTS = ["report_summary.py", "generate_dashboard_html.py", "export_network.py", "run_analyzers.py", "grounded_ratios.py", "generate_daily_summary.py"]
# A bare "exports/" path: not preceded by a path segment (data/, DATA_DIR/, <DATA_DIR>/) or a word char.
BARE_EXPORTS = re.compile(r"(?<![\w/>.-])exports/")


def test_scripts_write_under_data_dir_exports() -> None:
    for name in OUTPUT_SCRIPTS:
        src = (REPO / "scripts" / name).read_text(encoding="utf-8")
        assert 'db_path.parent / "exports"' in src, f"{name} no longer writes to DATA_DIR/exports; update docs and this test"


def test_user_docs_do_not_reference_repo_root_exports() -> None:
    offenders = []
    for doc in USER_DOCS:
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if BARE_EXPORTS.search(line):
                offenders.append(f"{doc.relative_to(REPO)}:{lineno}: {line.strip()[:120]}")
    assert not offenders, "Docs reference repo-root exports/; use <DATA_DIR>/exports/ (default data/exports/):\n" + "\n".join(offenders)

