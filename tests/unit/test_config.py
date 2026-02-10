# PURPOSE: Unit tests for config — lock in security behavior (require_api_key).
import pytest

from config import get_settings


def test_config_rejects_missing_api_key_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOLTBOOK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="MOLTBOOK_API_KEY"):
        get_settings(require_api_key=True)
