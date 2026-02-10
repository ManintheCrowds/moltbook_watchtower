# PURPOSE: Unit tests for Ollama client — request shape, 200 returns text, 500 raises.
from unittest.mock import patch

import pytest
import requests

from src.summary.ollama_client import OllamaError, generate


def test_generate_sends_correct_request_and_returns_text() -> None:
    with patch("src.summary.ollama_client.requests.post") as m:
        m.return_value.status_code = 200
        m.return_value.json.return_value = {"response": "Summary text here."}
        result = generate(
            base_url="http://localhost:11434",
            model="llama3.2",
            prompt="Say hello",
            timeout_seconds=60,
        )
        assert result == "Summary text here."
        m.assert_called_once()
        call_kw = m.call_args[1]
        assert call_kw["timeout"] == 60
        assert call_kw["json"]["model"] == "llama3.2"
        assert call_kw["json"]["prompt"] == "Say hello"
        assert call_kw["json"]["stream"] is False
        assert m.call_args[0][0] == "http://localhost:11434/api/generate"


def test_generate_500_raises_ollama_error() -> None:
    with patch("src.summary.ollama_client.requests.post") as m:
        m.return_value.status_code = 500
        with pytest.raises(OllamaError, match="500"):
            generate("http://localhost:11434", "llama3.2", "Hi", timeout_seconds=5)


def test_generate_connection_error_raises_ollama_error() -> None:
    with patch("src.summary.ollama_client.requests.post") as m:
        m.side_effect = requests.RequestException("Connection refused")
        with pytest.raises(OllamaError, match="request failed"):
            generate("http://localhost:11434", "llama3.2", "Hi", timeout_seconds=5)


def test_generate_empty_response_returns_empty_string() -> None:
    with patch("src.summary.ollama_client.requests.post") as m:
        m.return_value.status_code = 200
        m.return_value.json.return_value = {"response": None}
        result = generate("http://localhost:11434", "llama3.2", "Hi", timeout_seconds=5)
        assert result == ""
