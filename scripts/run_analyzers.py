#!/usr/bin/env python3
# PURPOSE: Run leak and injection analyzers; write findings to DB and alert file (redacted only); audit log.
# DEPENDENCIES: config, src.storage, src.analyzers, src.scheduler.audit
# MODIFICATION NOTES: Alerts contain post_id, rule_id, severity, redacted_snippet — never raw secret.

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.analyzers import (
    LeakAnalyzer,
    InjectionAnalyzer,
    BehaviorAnalyzer,
    LinguisticAnalyzer,
    Finding,
)
from src.scheduler.audit import audit_log
from src.storage import get_connection, StorageWriter


def write_alerts_file(settings, findings: list[Finding], analyzer_name: str) -> None:
    """Append redacted alerts to exports/alerts.txt (gitignored). No raw secrets."""
    exports = settings.db_path.parent / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    path = exports / "alerts.txt"
    with open(path, "a", encoding="utf-8") as f:
        for finding in findings:
            line = f"{analyzer_name}\tpost_id={finding.post_id}\tcomment_id={finding.comment_id}\trule={finding.rule_id}\tseverity={finding.severity}\tsnippet={finding.redacted_snippet or ''}\n"
            f.write(line)


def main() -> None:
    settings = get_settings(require_api_key=False)  # analyzers don't need API key
    leak_findings: list[Finding] = []
    inj_findings: list[Finding] = []
    behavior_findings: list[Finding] = []
    linguistic_findings: list[Finding] = []
    conn = get_connection(settings.db_path)
    cur = conn.cursor()
    try:
        leak_findings = list(LeakAnalyzer().run(cur))
        inj_findings = list(InjectionAnalyzer().run(cur))
        behavior_findings = list(BehaviorAnalyzer(cur).run())
        linguistic_findings = list(LinguisticAnalyzer().run(cur))
    finally:
        conn.close()

    writer = StorageWriter(settings.db_path)
    all_findings = (
        leak_findings
        + inj_findings
        + behavior_findings
        + linguistic_findings
    )
    writer.insert_findings(all_findings)

    audit_log(
        settings.audit_log_path,
        "run_analyzers",
        extra={
            "leak_count": len(leak_findings),
            "injection_count": len(inj_findings),
            "behavior_count": len(behavior_findings),
            "linguistic_count": len(linguistic_findings),
        },
    )
    if leak_findings:
        write_alerts_file(settings, leak_findings, "leak")
    if inj_findings:
        write_alerts_file(settings, inj_findings, "injection")
    if behavior_findings:
        write_alerts_file(settings, behavior_findings, "behavior")
    if linguistic_findings:
        write_alerts_file(settings, linguistic_findings, "linguistic")


if __name__ == "__main__":
    main()
