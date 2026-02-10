#!/usr/bin/env python3
# PURPOSE: Generate daily narrative summary via Ollama from DB data; no raw secrets in prompt.
# DEPENDENCIES: config, src.summary, src.scheduler.audit
# MODIFICATION NOTES: Best-effort; exit 0 on Ollama disabled or failure so daily run does not fail.

import os
import sys
from datetime import date
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.scheduler.audit import audit_log
from src.summary import get_daily_data, build_daily_summary_prompt, generate, OllamaError


def _report_date() -> str:
    """Report date as YYYY-MM-DD from env REPORT_DATE or today."""
    raw = os.getenv("REPORT_DATE", "").strip()
    if raw:
        return raw
    return date.today().isoformat()


def main() -> int:
    settings = get_settings(require_api_key=False)
    if not getattr(settings, "ollama_enabled", False):
        return 0

    report_date = _report_date()
    data = get_daily_data(settings.db_path, report_date)
    prompt = build_daily_summary_prompt(data)

    try:
        text = generate(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            prompt=prompt,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
    except OllamaError as e:
        print(f"Ollama summary skipped: {e}", file=sys.stderr)
        audit_log(
            settings.audit_log_path,
            "daily_summary_skipped",
            extra={"reason": "ollama_error", "error": str(e)[:200]},
        )
        return 0

    if not text:
        audit_log(settings.audit_log_path, "daily_summary_skipped", extra={"reason": "empty_response"})
        return 0

    # Write to DAILY_REPORT_DIR/YYYY-MM-DD-summary.md or data/exports/
    if getattr(settings, "daily_report_dir", None):
        out_dir = settings.daily_report_dir
    else:
        out_dir = settings.db_path.parent / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report_date}-summary.md"
    out_path.write_text(f"# Daily summary — {report_date}\n\n{text}", encoding="utf-8")
    print(f"Wrote {out_path}")

    audit_log(
        settings.audit_log_path,
        "daily_summary",
        extra={"report_date": report_date, "path": str(out_path)},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
