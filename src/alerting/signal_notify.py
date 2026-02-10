# PURPOSE: Signal alert stub — when SIGNAL_ENABLED set, call external mechanism (e.g. signal-cli); else no-op.
# DEPENDENCIES: config (optional)
# MODIFICATION NOTES: No live Signal dependency in CI; document real setup in runbook.

import logging
import subprocess
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)


def send_alert(title: str, body: str, settings: Optional["Settings"] = None) -> bool:
    """
    Send an alert (e.g. to Signal). When SIGNAL_ENABLED is set and SIGNAL_RECIPIENT is set,
    attempts to send via signal-cli. When disabled or no recipient, no-op or log-only.
    Returns True if no send was required or send succeeded; False if send was attempted and failed.
    """
    if settings is None:
        try:
            from config import get_settings
            settings = get_settings(require_api_key=False)
        except Exception:
            return True
    if not getattr(settings, "signal_enabled", False):
        return True
    prefix = getattr(settings, "signal_message_prefix", None) or ""
    message = f"{prefix}{title}: {body}".strip()
    recipient = getattr(settings, "signal_recipient", None) or ""
    if not recipient:
        logger.info("Signal alert (no recipient): %s", message)
        return True
    # Stub: try signal-cli if available (e.g. signal-cli send -a DEFAULT RECIPIENT -m "msg")
    try:
        # Typical: signal-cli -a <account> send <recipient> -m "<message>"
        # Recipient can be phone (+123...) or group ID. Account may be required.
        result = subprocess.run(
            ["signal-cli", "send", recipient, "-m", message],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("signal-cli send failed: %s", result.stderr or result.stdout)
            return False
        return True
    except FileNotFoundError:
        logger.warning("signal-cli not found; alert logged only: %s", message)
        return False
    except subprocess.TimeoutExpired:
        logger.warning("signal-cli send timed out")
        return False
    except Exception as e:
        logger.warning("Signal send error: %s", e)
        return False
