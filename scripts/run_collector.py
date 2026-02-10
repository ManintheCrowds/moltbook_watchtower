#!/usr/bin/env python3
# PURPOSE: One-shot or cron-invoked collector: fetch posts, feed, submolts; write to DB; audit log only metadata.
# DEPENDENCIES: config, src.client, src.storage, src.scheduler.audit
# MODIFICATION NOTES: No content in logs; rate limited GET only; optional jitter for cron.

import os
import random
import sys
import time
from pathlib import Path

# Allow running from repo root
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from config import get_settings
from src.alerting import send_alert
from src.client import MoltbookClient
from src.scheduler.audit import audit_log
from src.storage import StorageWriter, get_connection


def _maybe_jitter() -> None:
    """Optional delay 0--JITTER_SECONDS to desynchronize cron runs. Set JITTER_SECONDS=60 in env for cron."""
    sec = os.getenv("JITTER_SECONDS", "0").strip()
    if sec.isdigit() and int(sec) > 0:
        time.sleep(random.uniform(0, min(int(sec), 120)))


def _comment_fetch_limit() -> int:
    """Max posts to fetch comments for per run; cap 1–50. Env COMMENT_FETCH_LIMIT (default 25)."""
    raw = os.getenv("COMMENT_FETCH_LIMIT", "25").strip()
    if not raw.isdigit():
        return 25
    n = int(raw)
    return max(1, min(n, 50))


def main() -> None:
    _maybe_jitter()
    try:
        settings = get_settings(require_api_key=True)
        client = MoltbookClient(
            api_key=settings.moltbook_api_key,
            base_url=settings.moltbook_base_url,
            rate_limit_per_minute=settings.rate_limit_per_minute,
            timeout_seconds=settings.request_timeout_seconds,
        )
        writer = StorageWriter(settings.db_path)

        def _on_auth_failure(s: int, endpoint: str) -> None:
            if s in (401, 403):
                audit_log(settings.audit_log_path, "auth_failure", endpoint=endpoint, status=s)
                send_alert(
                    "Watchtower API auth failure",
                    f"status={s} endpoint={endpoint}",
                    settings=settings,
                )

        # Posts (new)
        status, body = client.get_posts(sort="new", limit=100)
        audit_log(
            settings.audit_log_path,
            "fetch_posts",
            endpoint="/api/v1/posts",
            status=status,
            record_count=writer.write_posts_response(body) if status == 200 else None,
        )
        if status != 200:
            audit_log(settings.audit_log_path, "fetch_posts_error", extra={"status": status})
            _on_auth_failure(status, "/api/v1/posts")

        # Feed (new)
        status, body = client.get_feed(sort="new", limit=100)
        audit_log(
            settings.audit_log_path,
            "fetch_feed",
            endpoint="/api/v1/feed",
            status=status,
            record_count=writer.write_posts_response(body) if status == 200 else None,
        )
        if status != 200:
            audit_log(settings.audit_log_path, "fetch_feed_error", extra={"status": status})
            _on_auth_failure(status, "/api/v1/feed")

        # Submolts
        status, body = client.get_submolts()
        audit_log(
            settings.audit_log_path,
            "fetch_submolts",
            endpoint="/api/v1/submolts",
            status=status,
            record_count=writer.write_submolts_response(body) if status == 200 else None,
        )
        if status != 200:
            audit_log(settings.audit_log_path, "fetch_submolts_error", extra={"status": status})
            _on_auth_failure(status, "/api/v1/submolts")

        # Comments for a bounded set of posts (simulated dialectics)
        limit = _comment_fetch_limit()
        conn = get_connection(settings.db_path)
        try:
            cur = conn.execute(
                "SELECT id FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            post_ids = [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
        for post_id in post_ids:
            status, body = client.get_post_comments(post_id, sort="new")
            count = writer.write_post_comments(post_id, body) if status == 200 else None
            audit_log(
                settings.audit_log_path,
                "fetch_comments",
                endpoint=f"/api/v1/posts/{post_id}/comments",
                status=status,
                record_count=count,
                extra={"post_id": post_id},
            )
            if status != 200:
                audit_log(
                    settings.audit_log_path,
                    "fetch_comments_error",
                    extra={"post_id": post_id, "status": status},
                )
                if status in (401, 403):
                    _on_auth_failure(status, f"/api/v1/posts/{post_id}/comments")
    except Exception as e:
        try:
            settings = get_settings(require_api_key=False)
            audit_log(
                settings.audit_log_path,
                "fetch_error",
                extra={"error_type": type(e).__name__},
            )
            send_alert(
                "Watchtower collector failed",
                f"{type(e).__name__}: {str(e)[:200]}",
                settings=settings,
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
