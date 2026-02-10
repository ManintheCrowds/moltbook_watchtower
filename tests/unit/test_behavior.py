# PURPOSE: Unit tests for behavior analyzer — fixture DB with windowed posts; assert findings and behavior_metrics.
from src.analyzers.behavior import BehaviorAnalyzer
from src.storage import get_connection, init_db


def test_behavior_analyzer_post_burst_yields_finding_and_metric(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = get_connection(db_path)
    for i in range(11):
        conn.execute(
            "INSERT INTO posts (id, agent_name, submolt, created_at) VALUES (?, ?, ?, datetime('now'))",
            (f"p{i}", "burst_agent", "s1"),
        )
    conn.commit()
    cur = conn.cursor()
    findings = list(BehaviorAnalyzer(cur).run())
    conn.close()
    assert any(f.rule_id == "behavior_post_burst" for f in findings)
    conn2 = get_connection(db_path)
    cur2 = conn2.cursor()
    cur2.execute("SELECT metric_type, key_name, value_int FROM behavior_metrics WHERE metric_type = 'posts_per_agent_window'")
    rows = cur2.fetchall()
    conn2.close()
    assert len(rows) >= 1
    assert any(r[1] == "burst_agent" and r[2] == 11 for r in rows)
