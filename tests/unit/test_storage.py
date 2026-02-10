# PURPOSE: Unit tests for storage writer — write_posts_response, write_post_comments, write_submolts_response, insert_findings, dedupe.
from src.analyzers.base import Finding
from src.storage import StorageWriter, get_connection, init_db


def test_init_db_creates_schema(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    assert db_path.exists()
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    assert cur.fetchone() is not None
    conn.close()


def test_write_posts_response_list(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    posts = [
        {"id": "p1", "title": "T1", "content": "C1", "author": {"name": "a1"}, "submolt": "s1", "created_at": "2025-01-01T00:00:00Z"},
        {"id": "p2", "title": "T2", "author": {"name": "a2"}, "submolt": "s1"},
    ]
    n = writer.write_posts_response(posts)
    assert n == 2
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, agent_name, submolt FROM posts ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] == "p1" and rows[0][1] == "a1" and rows[0][2] == "s1"
    assert rows[1][0] == "p2" and rows[1][1] == "a2" and rows[1][2] == "s1"


def test_write_posts_response_dict_with_posts_key(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    body = {"posts": [{"id": "p1", "title": "T1", "author": {"name": "a1"}, "submolt": "s1"}]}
    n = writer.write_posts_response(body)
    assert n == 1
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM posts")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_write_posts_response_empty_returns_zero(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    assert writer.write_posts_response(None) == 0
    assert writer.write_posts_response([]) == 0
    assert writer.write_posts_response({}) == 0


def test_write_submolts_response(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    items = [{"name": "s1", "display_name": "S1"}, {"name": "s2", "display_name": "S2"}]
    n = writer.write_submolts_response(items)
    assert n == 2
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name, display_name FROM submolts ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] == "s1" and rows[0][1] == "S1"
    assert rows[1][0] == "s2" and rows[1][1] == "S2"


def test_write_submolts_response_dict_with_submolts_key(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    body = {"submolts": [{"name": "s1", "display_name": "S1"}]}
    n = writer.write_submolts_response(body)
    assert n == 1
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM submolts")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_write_post_comments(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    comments = [
        {"id": "c1", "content": "x", "author": {"name": "a1"}},
        {"id": "c2", "content": "y", "parent_id": "c1"},
    ]
    n = writer.write_post_comments("p1", comments)
    assert n == 2
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, post_id, agent_name, parent_id FROM comments ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] == "c1" and rows[0][1] == "p1" and rows[0][2] == "a1" and rows[0][3] is None
    assert rows[1][0] == "c2" and rows[1][1] == "p1" and rows[1][3] == "c1"


def test_insert_findings_and_dedupe(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    findings = [
        Finding(post_id="p1", comment_id=None, rule_id="r1", severity="high", redacted_snippet="***"),
        Finding(post_id="p1", comment_id="c1", rule_id="r2", severity="medium", redacted_snippet="***"),
    ]
    writer.insert_findings(findings)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM findings")
    assert cur.fetchone()[0] == 2
    conn.close()
    writer.insert_findings(findings)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM findings WHERE post_id='p1' AND comment_id='c1' AND rule_id='r2'")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_insert_finding_single(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    writer = StorageWriter(db_path)
    writer.insert_finding("p1", None, "rule_x", "low", "snippet")
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT post_id, rule_id, severity FROM findings")
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "p1" and row[1] == "rule_x" and row[2] == "low"
