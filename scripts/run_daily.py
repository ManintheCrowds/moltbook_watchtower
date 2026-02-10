#!/usr/bin/env python3
# PURPOSE: Single daily-run entrypoint: optional canary, optional collector, analyzers, report, dashboard, export, optional Ollama summary.
# DEPENDENCIES: subprocess, sys, pathlib, os
# MODIFICATION NOTES: Env RUN_CANARY=1, MOLTBOOK_API_KEY, OLLAMA_ENABLED control steps; summary is best-effort.

import os
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
scripts_dir = repo_root / "scripts"


def main() -> int:
    if os.getenv("RUN_CANARY", "").strip().lower() in ("1", "true", "yes"):
        rc = subprocess.run(
            [sys.executable, str(scripts_dir / "check_canary.py")],
            cwd=str(repo_root),
            env=None,
        )
        if rc.returncode != 0:
            return rc.returncode

    if os.getenv("MOLTBOOK_API_KEY", "").strip():
        rc = subprocess.run(
            [sys.executable, str(scripts_dir / "run_collector.py")],
            cwd=str(repo_root),
            env=None,
        )
        if rc.returncode != 0:
            return rc.returncode

    for script in (
        "run_analyzers.py",
        "report_summary.py",
        "generate_dashboard_html.py",
        "export_network.py",
    ):
        rc = subprocess.run(
            [sys.executable, str(scripts_dir / script)],
            cwd=str(repo_root),
            env=None,
        )
        if rc.returncode != 0:
            return rc.returncode

    if os.getenv("OLLAMA_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        subprocess.run(
            [sys.executable, str(scripts_dir / "generate_daily_summary.py")],
            cwd=str(repo_root),
            env=None,
            check=False,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
