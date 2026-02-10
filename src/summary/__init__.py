# PURPOSE: Daily summary module — data fetch, prompt build, Ollama client.
# DEPENDENCIES: config, src.storage
# MODIFICATION NOTES: No raw content in prompts; redacted snippets only.

from .daily_data import get_daily_data
from .ollama_client import OllamaError, generate
from .prompt_builder import build_daily_summary_prompt

__all__ = ["get_daily_data", "build_daily_summary_prompt", "generate", "OllamaError"]
