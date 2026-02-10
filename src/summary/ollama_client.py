# PURPOSE: HTTP client for Ollama /api/generate; stream=false; timeout and error handling.
# DEPENDENCIES: requests
# MODIFICATION NOTES: On connection error or 5xx, raises OllamaError so caller can skip summary.

from typing import Optional

import requests


class OllamaError(Exception):
    """Raised when Ollama request fails (connection, timeout, 5xx)."""


def generate(
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int = 120,
) -> Optional[str]:
    """POST to {base_url}/api/generate with model and prompt; stream=false. Returns response text or None on failure."""
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=timeout_seconds)
    except requests.RequestException as e:
        raise OllamaError(f"Ollama request failed: {e}") from e
    if r.status_code >= 500:
        raise OllamaError(f"Ollama server error: {r.status_code}")
    if r.status_code != 200:
        raise OllamaError(f"Ollama returned {r.status_code}")
    data = r.json()
    if not isinstance(data, dict):
        raise OllamaError("Ollama response is not JSON object")
    text = data.get("response")
    if text is None:
        return ""
    return str(text).strip()
