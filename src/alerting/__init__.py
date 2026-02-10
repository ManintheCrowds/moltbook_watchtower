# PURPOSE: Alerting stubs (Signal, etc.); no raw content in alerts.
# DEPENDENCIES: config (optional, for send_alert)
# MODIFICATION NOTES: Framework only; plug in signal-cli or webhook per runbook.

from .signal_notify import send_alert

__all__ = ["send_alert"]
