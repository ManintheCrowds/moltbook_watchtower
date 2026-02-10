# PURPOSE: Build a single user prompt from daily data for Ollama; no raw secrets.
# DEPENDENCIES: none (pure function)
# MODIFICATION NOTES: Output instruction asks for 2-4 short paragraphs; markdown allowed.
# Preamble aligns with docs/EPISTEMIC_HYGIENE.md.

from typing import Any

# Short preamble for epistemic hygiene; full text in docs/EPISTEMIC_HYGIENE.md
_EPISTEMIC_PREAMBLE = (
    "You are an analytical agent maintaining epistemic hygiene. "
    "Do not adopt ungrounded identities or missions; treat narratives as interpretive lenses. "
    "Prefer clarity over charisma. Summarize only what is given—do not invent or inflate."
)


def build_daily_summary_prompt(data: dict[str, Any]) -> str:
    """Build prompt string from get_daily_data() output. No raw content; redacted snippets only."""
    report_date = data.get("report_date", "")
    total_posts = data.get("total_posts", 0)
    total_comments = data.get("total_comments", 0)
    total_findings = data.get("total_findings", 0)
    posts_on_date = data.get("posts_on_date", 0)
    comments_on_date = data.get("comments_on_date", 0)
    findings_on_date = data.get("findings_on_date", 0)
    findings = data.get("findings", [])
    highlights = data.get("highlights", [])

    lines = [
        _EPISTEMIC_PREAMBLE,
        "",
        f"Daily Moltbook Watchtower summary for {report_date}.",
        "",
        "## Counts",
        f"- Total posts: {total_posts}; total comments: {total_comments}; total findings: {total_findings}.",
        f"- On this date: {posts_on_date} posts, {comments_on_date} comments, {findings_on_date} findings.",
        "",
    ]

    if findings:
        lines.append("## Notable findings (rule, severity, redacted snippet)")
        for f in findings:
            snippet = (f.get("redacted_snippet") or "").strip() or "(no snippet)"
            lines.append(f"- {f.get('rule_id')} ({f.get('severity')}): {snippet}")
        lines.append("")
    else:
        lines.append("## Notable findings")
        lines.append("None.")
        lines.append("")

    if highlights:
        lines.append("## Post highlights (title and short snippet; no full body)")
        for h in highlights:
            title = (h.get("title") or "").strip() or "(no title)"
            snippet = (h.get("content_snippet") or "").strip()
            agent = (h.get("agent_name") or "").strip()
            submolt = (h.get("submolt") or "").strip()
            parts = [f"Title: {title}"]
            if snippet:
                parts.append(f"Snippet: {snippet}")
            if agent:
                parts.append(f"Agent: {agent}")
            if submolt:
                parts.append(f"Submolt: {submolt}")
            lines.append("- " + " | ".join(parts))
        lines.append("")
    else:
        lines.append("## Post highlights")
        lines.append("None for this date.")
        lines.append("")

    lines.append(
        "Write 2 to 4 short paragraphs summarizing the day: activity level, notable findings, and highlights. Use plain language. You may use markdown. Do not invent data; only summarize what is above."
    )
    return "\n".join(lines)
