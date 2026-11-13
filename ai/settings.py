"""AI provider settings resolution.

Configuration is read from, in order:

1. Explicit overrides passed by the caller (tests and scripts).
2. Streamlit secrets (``.streamlit/secrets.toml``).
3. Process environment variables.

The Deploy provider issues its key as ``DEPLOY_API_KEY``, so that name is
accepted as a fallback for ``AI_API_KEY``. The key is never logged, never
echoed in ``repr`` and never written into a prompt.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "https://api-cdn.deploy.com/api/v1"
DEFAULT_MODEL = "deepseek-ai/deepseek-v4.1-flash-1017"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TEMPERATURE = 0.2

# The model is a reasoning model: it spends completion tokens on internal
# reasoning before writing an answer. A capped response is silently truncated,
# so the ceiling must be generous.
MIN_USEFUL_MAX_TOKENS = 3000

KEY_NAMES = ("AI_API_KEY", "DEPLOY_API_KEY")
BASE_URL_NAMES = ("AI_BASE_URL",)
MODEL_NAMES = ("AI_MODEL",)


@dataclass(frozen=True)
class AISettings:
    """Resolved provider configuration."""

    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    source: str = field(default="default", repr=False)

    @property
    def is_configured(self) -> bool:
        """True when a non-empty API key is available."""

        return bool(self.api_key.strip())

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def __repr__(self) -> str:  # pragma: no cover - defensive formatting
        key_state = f"set:{len(self.api_key)}" if self.api_key else "absent"
        return (
            f"AISettings(base_url={self.base_url!r}, model={self.model!r}, "
            f"api_key=<{key_state}>, source={self.source!r})"
        )


def _mapping_value(sources: Sequence[Mapping[str, object]], names):
    for source in sources:
        for name in names:
            value = source.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _streamlit_secrets() -> Mapping[str, object]:
    """Return Streamlit secrets, or an empty mapping outside a runtime.

    The AI layer must work in plain Python too (tests, CLI checks), so any
    failure to reach the Streamlit secrets subsystem degrades to "no secrets"
    rather than breaking the request.
    """

    try:  # pragma: no cover - depends on the Streamlit runtime
        import streamlit as st

        secrets = st.secrets
    except Exception:  # noqa: BLE001 - secrets unavailable outside Streamlit
        return {}

    try:
        return dict(secrets)
    except Exception:  # noqa: BLE001 - malformed secrets file
        return {}


def _environment() -> Mapping[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if name in KEY_NAMES or name in BASE_URL_NAMES or name in MODEL_NAMES
    }


def load_settings(
    overrides: Mapping[str, object] | None = None,
) -> AISettings:
    """Resolve provider settings from overrides, secrets and environment."""

    sources: list[Mapping[str, object]] = []
    if overrides:
        sources.append(overrides)
    secrets = _streamlit_secrets()
    if secrets:
        sources.append(secrets)
    sources.append(_environment())

    api_key = _mapping_value(sources, KEY_NAMES) or ""
    base_url = _mapping_value(sources, BASE_URL_NAMES) or DEFAULT_BASE_URL
    model = _mapping_value(sources, MODEL_NAMES) or DEFAULT_MODEL

    if overrides and any(name in overrides for name in KEY_NAMES):
        source = "override"
    elif secrets and any(name in secrets for name in KEY_NAMES):
        source = "secrets"
    elif any(name in os.environ for name in KEY_NAMES):
        source = "environment"
    else:
        source = "default"

    return AISettings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        source=source,
    )
