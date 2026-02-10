# Adding a New Analyzer

How to plug in a new analyzer so it runs with leak, injection, behavior, and linguistic.

## Interface

- **Input:** A `sqlite3.Cursor` over the Watchtower DB (posts, comments, findings, etc.). Your analyzer runs `cursor.execute(...)` and `cursor.fetchall()` to read stored content. Do not log or emit raw post/comment content.
- **Output:** An iterator of `Finding` objects. Each has:
  - `post_id` (optional)
  - `comment_id` (optional)
  - `rule_id` (str) — e.g. `"my_rule"`
  - `severity` (str) — e.g. `"high"`, `"medium"`, `"low"`
  - `redacted_snippet` (optional) — safe summary only; **never the actual secret or full content.**

## Steps

1. **Create a module** under `src/analyzers/`, e.g. `src/analyzers/my_analyzer.py`.
2. **Implement a class** with a `run(self, cursor)` method that yields `Finding` instances:

   ```python
   from .base import Finding

   class MyAnalyzer:
       def run(self, cursor):
           cursor.execute("SELECT id, title, content FROM posts")
           for row in cursor.fetchall():
               # ... scan row, yield Finding(...)
   ```

3. **Register in `src/analyzers/__init__.py`:** Export the class and add it to `__all__`.
4. **Wire into `scripts/run_analyzers.py`:** Instantiate your analyzer, call `run(cur)`, persist findings via `writer.insert_finding(...)`, and optionally append to the alerts file and audit log (same pattern as leak/injection/behavior).

## Rules

- Do not log or return raw secrets or full post/comment bodies.
- Use `redacted_snippet` for debugging (e.g. `"rule_id match"` or `"Bearer ***"`).
- Findings are stored in the `findings` table and can be included in exports and the dashboard.

## Linguistic analyzer and rule_id prefixes

The **linguistic** analyzer (`LinguisticAnalyzer`) uses rule_id **prefixes** for grouping: `ling_*`, `behav_*`, `drift_*`, `grounded_*`. See [LINGUISTIC_MONITOR.md](LINGUISTIC_MONITOR.md) for the full rule_id reference and behavior.

## Optional: YARA or external rules

If Moltbook later exposes skill files or downloadable content, you can add an analyzer that:
- Fetches or reads those artifacts (read-only),
- Runs YARA or regex rules from a config file,
- Emits `Finding` with `rule_id` set to the rule name and `redacted_snippet` as a safe summary.
