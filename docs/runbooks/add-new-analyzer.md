# Runbook: Add a new analyzer

## Purpose

Add a new analysis rule (e.g. new leak pattern, new behavior metric) that runs with the existing leak, injection, and behavior analyzers and writes findings to the DB and alert file.

## Steps

1. **Implement the analyzer** per [ADDING_ANALYZERS.md](../ADDING_ANALYZERS.md):
   - Implement the interface (e.g. `run(cursor)` yielding `Finding` objects).
   - Place in `src/analyzers/` (e.g. `src/analyzers/your_analyzer.py`).

2. **Register in run_analyzers.py:**
   - Import the analyzer class.
   - Get a cursor from `get_connection(settings.db_path)`.
   - Call `YourAnalyzer().run(cur)` and collect findings.
   - Append findings to the list passed to `writer.insert_findings(...)`.
   - Optionally append to alerts file (redacted only) and audit_log with a count for the new analyzer.

3. **Run the pipeline:** After registration, `python scripts/run_analyzers.py` will run the new analyzer with the others. No change to collector or report required unless you want new dashboard/report columns.

## Reference

- [ADDING_ANALYZERS.md](../ADDING_ANALYZERS.md) — interface, Finding dataclass, and examples.
