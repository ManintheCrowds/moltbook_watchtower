#!/usr/bin/env python3
# PURPOSE: Run analyzers, report, dashboard, and export without calling the Moltbook API.
# DEPENDENCIES: subprocess, sys, pathlib; invokes run_analyzers, report_summary, generate_dashboard_html, export_network.
# MODIFICATION NOTES: No MOLTBOOK_API_KEY required; uses existing DB only.

import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
scripts_dir = repo_root / "scripts"


def main() -> None:
    steps = [
        "run_analyzers.py",
        "report_summary.py",
        "generate_dashboard_html.py",
        "export_network.py",
    ]
    for script in steps:
        rc = subprocess.run(
            [sys.executable, str(scripts_dir / script)],
            cwd=str(repo_root),
            env=None,
        )
        if rc.returncode != 0:
            sys.exit(rc.returncode)


if __name__ == "__main__":
    main()
