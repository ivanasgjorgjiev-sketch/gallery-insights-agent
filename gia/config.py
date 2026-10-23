"""Runtime configuration: API key, model and limits.

Values come from environment variables or Streamlit secrets (.streamlit/secrets.toml
locally, the app's Secrets settings on Streamlit Community Cloud). The API key is
never logged, displayed or written into traces.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_EFFORT = "medium"
DEFAULT_MAX_TOOL_CALLS = 15
DEFAULT_MAX_ANALYSES_PER_SESSION = 5

# Published per-million-token prices (USD) used only for the cost estimate shown in the app.
PRICES_PER_MTOK = {
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
}


def _setting(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # no secrets file, or not running under Streamlit
        pass
    return None


def api_key() -> str | None:
    return _setting("ANTHROPIC_API_KEY")


def model() -> str:
    return _setting("GIA_MODEL") or DEFAULT_MODEL


def effort() -> str:
    return _setting("GIA_EFFORT") or DEFAULT_EFFORT


def max_tool_calls() -> int:
    return int(_setting("GIA_MAX_TOOL_CALLS") or DEFAULT_MAX_TOOL_CALLS)


def max_analyses_per_session() -> int:
    return int(_setting("GIA_MAX_ANALYSES_PER_SESSION") or DEFAULT_MAX_ANALYSES_PER_SESSION)
