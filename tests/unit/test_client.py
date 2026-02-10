# PURPOSE: Unit tests for Moltbook client — lock in base URL restriction.
import pytest

from src.client import MoltbookClient


def test_client_rejects_non_moltbook_base_url() -> None:
    with pytest.raises(ValueError, match="https://www.moltbook.com"):
        MoltbookClient(api_key="fake_key", base_url="https://evil.com")
