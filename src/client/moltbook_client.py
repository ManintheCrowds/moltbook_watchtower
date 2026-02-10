# PURPOSE: Moltbook API client — GET only, rate limit 90/min, backoff on 429/5xx.
# DEPENDENCIES: requests, config.settings. API key sent ONLY to https://www.moltbook.com.
# MODIFICATION NOTES: No POST; single watchdog agent.

import time
from typing import Any, Optional

import requests

# Allowed host for API key — do not send key to any other host
_ALLOWED_BASE = "https://www.moltbook.com"


class MoltbookClient:
    """Read-only Moltbook API client. GET only; rate limited; backoff on 429/5xx."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _ALLOWED_BASE,
        rate_limit_per_minute: int = 90,
        timeout_seconds: int = 30,
    ):
        if not base_url.rstrip("/").startswith(_ALLOWED_BASE):
            raise ValueError(
                f"API key may only be used with {_ALLOWED_BASE}. Got base_url={base_url!r}"
            )
        self._base = base_url.rstrip("/")
        self._api_base = f"{self._base}/api/v1"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MoltbookClient/1.0",
        }
        self._session = requests.Session()
        self._session.headers.update(self._headers)
        self._timeout = timeout_seconds
        self._min_interval = 60.0 / rate_limit_per_minute if rate_limit_per_minute else 0
        self._last_request_time: float = 0

    def _wait_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> tuple[int, Any]:
        """GET path (relative to api/v1). Returns (status_code, json_body or None)."""
        url = f"{self._api_base}/{path.lstrip('/')}"
        self._wait_rate_limit()
        for attempt in range(max_retries):
            try:
                r = self._session.get(url, params=params, timeout=self._timeout)
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 60))
                time.sleep(min(retry_after, 120))
                continue
            if 500 <= r.status_code < 600 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            try:
                body = r.json() if r.content else None
            except Exception:
                body = None
            return r.status_code, body
        return 503, None

    def get_posts(self, sort: str = "new", limit: int = 100) -> tuple[int, Any]:
        """GET /api/v1/posts?sort=&limit=."""
        return self._get("posts", params={"sort": sort, "limit": limit})

    def get_feed(self, sort: str = "new", limit: int = 100) -> tuple[int, Any]:
        """GET /api/v1/feed?sort=&limit=."""
        return self._get("feed", params={"sort": sort, "limit": limit})

    def get_submolts(self) -> tuple[int, Any]:
        """GET /api/v1/submolts."""
        return self._get("submolts")

    def get_post(self, post_id: str) -> tuple[int, Any]:
        """GET /api/v1/posts/<id>."""
        return self._get(f"posts/{post_id}")

    def get_post_comments(self, post_id: str, sort: str = "new") -> tuple[int, Any]:
        """GET /api/v1/posts/<id>/comments."""
        return self._get(f"posts/{post_id}/comments", params={"sort": sort})

    def get_agents_status(self) -> tuple[int, Any]:
        """GET /api/v1/agents/status."""
        return self._get("agents/status")

    def get_agent_profile(self, name: str) -> tuple[int, Any]:
        """GET /api/v1/agents/profile?name=."""
        return self._get("agents/profile", params={"name": name})
