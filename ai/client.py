"""HTTP client for the OpenAI-compatible Deploy provider.

The transport is :mod:`urllib` from the standard library, so the project does
not gain a heavyweight SDK dependency. Retries are bounded and only applied to
429 and 5xx responses; a timeout, an authentication failure or a malformed
response fails immediately.

The API key is placed in the ``Authorization`` header and nowhere else. It is
never logged, never echoed in an exception message and never included in
:class:`AICompletion`.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AINetworkError,
    AIRateLimitError,
    AIResponseError,
    AIServerError,
    AITimeoutError,
)
from ai.settings import MIN_USEFUL_MAX_TOKENS, AISettings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRY_DELAYS = (1.0, 3.0)


@dataclass(frozen=True)
class AIUsage:
    """Token accounting reported by the provider."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def as_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "reasoning_tokens": self.reasoning_tokens,
        }


@dataclass(frozen=True)
class AICompletion:
    """A validated completion returned by the provider."""

    content: str
    model: str = ""
    finish_reason: str = ""
    usage: AIUsage = field(default_factory=AIUsage)
    attempts: int = 1

    def __repr__(self) -> str:  # pragma: no cover - defensive formatting
        return (
            f"AICompletion(model={self.model!r}, chars={len(self.content)}, "
            f"finish_reason={self.finish_reason!r}, attempts={self.attempts})"
        )


def _error_message(payload: Any) -> str:
    """Extract a message from either the OpenAI or the Deploy error shape."""

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        if isinstance(error, str) and error.strip():
            return error.strip()
        # Deploy returns {"message": ..., "status_code": ...}
        for name in ("message", "detail", "error_description"):
            message = payload.get(name)
            if isinstance(message, str) and message.strip():
                return message.strip()
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return "The AI provider rejected the request."


def _classify_http_error(status: int, message: str) -> AIError:
    if status in (401, 403):
        return AIAuthenticationError(
            "The AI provider rejected the API key. Check the key in "
            "secrets.toml or the DEPLOY_API_KEY environment variable."
        )
    if status == 429:
        return AIRateLimitError(
            "The AI provider is rate limiting requests. Try again later."
        )
    if status >= 500:
        return AIServerError(
            f"The AI provider reported a server error ({status}). Try again later."
        )
    if status == 408:
        return AITimeoutError("The AI provider timed out before responding.")
    return AIError(f"The AI provider rejected the request ({status}): {message}")


class AIClient:
    """Minimal OpenAI-compatible chat client with bounded retries."""

    def __init__(
        self,
        settings: AISettings | None = None,
        *,
        transport=None,
        retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
        sleep=time.sleep,
    ) -> None:
        self.settings = settings or AISettings()
        self._transport = transport or _urllib_transport
        self._retry_delays = tuple(retry_delays)
        self._sleep = sleep

    # -- public API --------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when the client has a key and can attempt a request."""

        return self.settings.is_configured

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> AICompletion:
        """Send a chat completion request and return validated content."""

        if not self.settings.is_configured:
            raise AIConfigurationError(
                "No AI API key is configured. Add AI_API_KEY to "
                ".streamlit/secrets.toml or set the DEPLOY_API_KEY environment "
                "variable."
            )
        if not messages:
            raise ValueError("At least one chat message is required.")

        requested_tokens = max_tokens or self.settings.max_tokens
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "max_tokens": max(
                int(requested_tokens), MIN_USEFUL_MAX_TOKENS
            ),
            "temperature": (
                self.settings.temperature if temperature is None else temperature
            ),
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        attempts_allowed = max(0, int(self.settings.max_retries)) + 1
        last_error: AIError | None = None

        for attempt in range(1, attempts_allowed + 1):
            try:
                raw = self._transport(
                    self.settings.chat_completions_url,
                    payload,
                    self.settings.api_key,
                    self.settings.timeout_seconds,
                )
            except AIError as exc:
                last_error = exc
                if _is_retryable(exc) and attempt < attempts_allowed:
                    self._pause(attempt)
                    continue
                raise
            else:
                return _parse_completion(raw, attempts=attempt)

        # Every attempt raised a retryable error.
        assert last_error is not None
        raise last_error

    def _pause(self, attempt: int) -> None:
        index = min(attempt - 1, len(self._retry_delays) - 1)
        if index >= 0:
            self._sleep(self._retry_delays[index])


def _is_retryable(error: AIError) -> bool:
    return isinstance(error, (AIRateLimitError, AIServerError))


def _urllib_transport(
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout: float,
) -> bytes:
    """POST ``payload`` as JSON and return the raw response body."""

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raw = b""
        try:
            raw = exc.read()
        except (OSError, ValueError):  # pragma: no cover - body consumed
            raw = b""
        message = _error_message(_safe_json(raw))
        raise _classify_http_error(exc.code, message) from None
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
            raise AITimeoutError("The AI provider did not respond in time.") from None
        raise AINetworkError(
            "The AI provider could not be reached. Check the network connection."
        ) from None
    except TimeoutError:
        raise AITimeoutError("The AI provider did not respond in time.") from None


def _safe_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")


def _parse_completion(raw: bytes, *, attempts: int) -> AICompletion:
    """Validate the provider envelope and return the message content."""

    payload = _safe_json(raw)
    if not isinstance(payload, dict):
        raise AIResponseError(
            "The AI provider returned a response that is not a JSON object."
        )

    if "error" in payload and "choices" not in payload:
        raise AIError(_error_message(payload))

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIResponseError(
            "The AI provider returned no completion choices. This can happen "
            "when the token budget is exhausted before any content is written."
        )

    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message")
    content = ""
    if isinstance(message, dict):
        raw_content = message.get("content")
        if isinstance(raw_content, str):
            content = raw_content.strip()
    if not content:
        raw_content = first.get("text")
        if isinstance(raw_content, str):
            content = raw_content.strip()

    finish_reason = first.get("finish_reason")
    if not content:
        raise AIResponseError(
            "The AI provider returned an empty completion. The model may have "
            "spent its whole token budget on internal reasoning; raise "
            "max_tokens and try again."
        )
    if finish_reason == "length":
        raise AIResponseError(
            "The AI provider truncated the response before it finished. The "
            "token ceiling was reached, so the answer is incomplete and cannot "
            "be trusted; raise max_tokens and try again."
        )

    return AICompletion(
        content=content,
        model=str(payload.get("model") or ""),
        finish_reason=str(finish_reason or ""),
        usage=_parse_usage(payload.get("usage")),
        attempts=attempts,
    )


def _parse_usage(usage: Any) -> AIUsage:
    if not isinstance(usage, dict):
        return AIUsage()

    def as_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    details = usage.get("completion_tokens_details")
    reasoning = as_int(details.get("reasoning_tokens")) if isinstance(details, dict) else 0
    return AIUsage(
        prompt_tokens=as_int(usage.get("prompt_tokens")),
        completion_tokens=as_int(usage.get("completion_tokens")),
        total_tokens=as_int(usage.get("total_tokens")),
        reasoning_tokens=reasoning,
    )
