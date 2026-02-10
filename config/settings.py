# PURPOSE: Env-based config; base URL must be https://www.moltbook.com for API key use.
# DEPENDENCIES: os, pathlib, python-dotenv
# MODIFICATION NOTES: Single source of truth for MOLTBOOK_API_KEY and paths.

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Allowed base URL for API requests — key is sent ONLY here
MOLTBOOK_BASE_URL = "https://www.moltbook.com"
MOLTBOOK_API_BASE = f"{MOLTBOOK_BASE_URL}/api/v1"


def get_settings(require_api_key: bool = True) -> "Settings":
    """Load settings from env. If require_api_key=True, raises if MOLTBOOK_API_KEY missing."""
    api_key = os.getenv("MOLTBOOK_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise ValueError(
            "MOLTBOOK_API_KEY must be set (e.g. in .env). "
            "Use a dedicated watchdog agent key for read-only access."
        )
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    signal_enabled = (os.getenv("SIGNAL_ENABLED", "").strip().lower() in ("1", "true", "yes"))
    signal_recipient = os.getenv("SIGNAL_RECIPIENT", "").strip() or None
    signal_message_prefix = os.getenv("SIGNAL_MESSAGE_PREFIX", "").strip() or None
    daily_report_dir_raw = os.getenv("DAILY_REPORT_DIR", "").strip()
    daily_report_dir = Path(daily_report_dir_raw) if daily_report_dir_raw else None
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2"
    ollama_enabled = os.getenv("OLLAMA_ENABLED", "").strip().lower() in ("1", "true", "yes")
    ollama_timeout_raw = os.getenv("OLLAMA_TIMEOUT_SECONDS", "120").strip()
    ollama_timeout_seconds = int(ollama_timeout_raw) if ollama_timeout_raw.isdigit() else 120
    return Settings(
        moltbook_api_key=api_key,
        moltbook_base_url=MOLTBOOK_BASE_URL,
        moltbook_api_base=MOLTBOOK_API_BASE,
        data_dir=data_dir,
        log_dir=log_dir,
        db_path=data_dir / "watchtower.db",
        audit_log_path=log_dir / "audit.jsonl",
        rate_limit_per_minute=90,
        request_timeout_seconds=30,
        signal_enabled=signal_enabled,
        signal_recipient=signal_recipient,
        signal_message_prefix=signal_message_prefix,
        daily_report_dir=daily_report_dir,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_enabled=ollama_enabled,
        ollama_timeout_seconds=ollama_timeout_seconds,
    )


class Settings:
    __slots__ = (
        "moltbook_api_key",
        "moltbook_base_url",
        "moltbook_api_base",
        "data_dir",
        "log_dir",
        "db_path",
        "audit_log_path",
        "rate_limit_per_minute",
        "request_timeout_seconds",
        "signal_enabled",
        "signal_recipient",
        "signal_message_prefix",
        "daily_report_dir",
        "ollama_base_url",
        "ollama_model",
        "ollama_enabled",
        "ollama_timeout_seconds",
    )

    def __init__(
        self,
        *,
        moltbook_api_key: str,
        moltbook_base_url: str,
        moltbook_api_base: str,
        data_dir: Path,
        log_dir: Path,
        db_path: Path,
        audit_log_path: Path,
        rate_limit_per_minute: int = 90,
        request_timeout_seconds: int = 30,
        signal_enabled: bool = False,
        signal_recipient: str | None = None,
        signal_message_prefix: str | None = None,
        daily_report_dir: Optional[Path] = None,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
        ollama_enabled: bool = False,
        ollama_timeout_seconds: int = 120,
    ):
        self.moltbook_api_key = moltbook_api_key
        self.moltbook_base_url = moltbook_base_url
        self.moltbook_api_base = moltbook_api_base
        self.data_dir = data_dir
        self.log_dir = log_dir
        self.db_path = db_path
        self.audit_log_path = audit_log_path
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_timeout_seconds = request_timeout_seconds
        self.signal_enabled = signal_enabled
        self.signal_recipient = signal_recipient
        self.signal_message_prefix = signal_message_prefix
        self.daily_report_dir = daily_report_dir
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.ollama_enabled = ollama_enabled
        self.ollama_timeout_seconds = ollama_timeout_seconds