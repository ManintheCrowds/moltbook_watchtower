# PURPOSE: Unit tests for alerting — send_alert when disabled returns True and does not call subprocess.
from unittest.mock import MagicMock

import pytest

from src.alerting.signal_notify import send_alert


def test_send_alert_when_disabled_returns_true_no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_run = MagicMock()
    monkeypatch.setattr("src.alerting.signal_notify.subprocess.run", mock_run)
    settings = MagicMock()
    settings.signal_enabled = False
    settings.signal_recipient = "+1234567890"
    result = send_alert("Test", "body", settings=settings)
    assert result is True
    mock_run.assert_not_called()


def test_send_alert_when_no_recipient_returns_true_no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_run = MagicMock()
    monkeypatch.setattr("src.alerting.signal_notify.subprocess.run", mock_run)
    settings = MagicMock()
    settings.signal_enabled = True
    settings.signal_recipient = ""
    result = send_alert("Test", "body", settings=settings)
    assert result is True
    mock_run.assert_not_called()
