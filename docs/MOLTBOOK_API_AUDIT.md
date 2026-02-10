# Moltbook API Audit — Watchtower vs skill.md

Reference: [Moltbook skill.md](https://www.moltbook.com/skill.md). This doc maps endpoints we use to our code and response handling.

## Endpoints we use

| Endpoint | skill.md | Client method | Writer / usage | Collector |
|----------|----------|---------------|----------------|-----------|
| GET /api/v1/posts?sort=&limit= | Get feed / posts | `get_posts(sort, limit)` | `write_posts_response(body)` | Yes — posts (new, 100) |
| GET /api/v1/feed?sort=&limit= | Your personalized feed | `get_feed(sort, limit)` | `write_posts_response(body)` | Yes — feed (new, 100) |
| GET /api/v1/submolts | List all submolts | `get_submolts()` | `write_submolts_response(body)` | Yes |
| GET /api/v1/posts/<id> | Get a single post | `get_post(post_id)` | — | No (not used) |
| GET /api/v1/posts/<id>/comments?sort= | Get comments on a post | `get_post_comments(post_id, sort)` | `write_post_comments(post_id, body)` | Yes — bounded post set |
| GET /api/v1/agents/status | Check claim status | `get_agents_status()` | — | No |
| GET /api/v1/agents/profile?name= | View another molty's profile | `get_agent_profile(name)` | — | No |

## Response shapes (skill.md vs our parsing)

- **Posts / feed:** skill.md shows `curl "posts?sort=hot&limit=25"`; typical shape is an array of post objects or `{ "posts": [...] }` / `{ "data": [...] }`. We accept: body as list, or `body.get("posts")` / `body.get("data")` / `body.get("results")` → list. See `writer.write_posts_response` (posts/feed).
- **Submolts:** GET submolts returns list or `{ "submolts": [...] }` / `{ "data": [...] }`. We accept: body as list, or `body.get("submolts")` / `body.get("data")`. See `writer.write_submolts_response`.
- **Comments:** GET posts/<id>/comments; shape not fully specified in skill.md; we accept: body as list, or `body.get("comments")` / `body.get("data")`. See `writer.write_post_comments` (L206–211).

## Rate limits

| Source | Limit |
|--------|--------|
| skill.md | 100 requests/minute; 1 post/30 min; 1 comment/20 s; 50 comments/day |
| Our client | 90 requests/minute (configurable `rate_limit_per_minute`). No POST. |

We stay under 100/min by default. Comment fetches are bounded per run via `COMMENT_FETCH_LIMIT` (default 25, max 50).

## Base URL and security

- skill.md: **Always use `https://www.moltbook.com`** (with www); redirect without www can strip Authorization.
- Our client: `_ALLOWED_BASE = "https://www.moltbook.com"`; `base_url` must start with it or we raise. API key is only sent to this host.

## Audit against GitHub

When the Moltbook API spec or backend repo is available:

- Diff endpoint list (e.g. from OpenAPI or route definitions) against this audit.
- Compare response schemas for GET posts, feed, submolts, comments to our writer parsing.
- Re-check rate limit values and any new headers (e.g. Retry-After).

**Status:** Pending — audit when Moltbook API spec or backend repo is available.
