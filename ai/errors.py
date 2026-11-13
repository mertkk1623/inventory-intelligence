"""Typed exceptions for the AI Intelligence Layer.

Every failure the layer can produce is one of these classes, which lets the UI
degrade gracefully instead of crashing when the provider is unavailable.
"""

from __future__ import annotations


class AIError(Exception):
    """Base class for every AI layer failure."""


class AIConfigurationError(AIError):
    """The API key or provider configuration is missing or unusable."""


class AIAuthenticationError(AIError):
    """The provider rejected the credentials (HTTP 401 or 403)."""


class AIRateLimitError(AIError):
    """The provider is rate limiting requests (HTTP 429)."""


class AIServerError(AIError):
    """The provider returned a server error (HTTP 5xx)."""


class AITimeoutError(AIError):
    """The request exceeded the configured timeout."""


class AINetworkError(AIError):
    """The provider could not be reached."""


class AIResponseError(AIError):
    """The response was not valid JSON or did not match the schema."""
