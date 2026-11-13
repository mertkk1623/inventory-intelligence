"""AI Intelligence Layer for Inventory Intelligence.

The package interprets the deterministic calculation engine result in natural
language. It never calculates inventory values itself: every number sent to
the model comes from :class:`core.models.InventoryCalculation`.
"""

from __future__ import annotations

from ai.cache import AICache, default_cache
from ai.client import AIClient, AICompletion
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
from ai.insights import (
    explain_replenishment,
    generate_consumption_insights,
    generate_inventory_insights,
)
from ai.inventory_analyst import answer_question
from ai.settings import AISettings, load_settings

__all__ = [
    "AIAuthenticationError",
    "AICache",
    "AIClient",
    "AICompletion",
    "AIConfigurationError",
    "AIError",
    "AINetworkError",
    "AIRateLimitError",
    "AIResponseError",
    "AIServerError",
    "AISettings",
    "AITimeoutError",
    "answer_question",
    "default_cache",
    "explain_replenishment",
    "generate_consumption_insights",
    "generate_inventory_insights",
    "load_settings",
]
