"""AI insight generation: inventory, consumption and replenishment.

Every function takes the engine result that the UI already displays, builds a
safe context, asks the provider for structured JSON and validates the answer.
Successful answers are cached by context fingerprint. Failures propagate as
:class:`~ai.errors.AIError` subclasses and are never cached.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ai.cache import AICache, default_cache
from ai.client import AIClient
from ai.context_builder import AIContext, build_ai_context
from ai.prompts import (
    consumption_insights_messages,
    inventory_insights_messages,
    replenishment_messages,
)
from ai.schemas import (
    ConsumptionInsightResponse,
    InventoryInsightResponse,
    ReplenishmentExplanation,
    validate_response,
)
from core.models import InventoryCalculation, InventoryDataset

OPERATION_INVENTORY = "inventory-insights"
OPERATION_CONSUMPTION = "consumption-insights"
OPERATION_REPLENISHMENT = "replenishment-explanation"


@dataclass(frozen=True)
class InsightResult:
    """A validated insight plus the provenance the UI must show."""

    value: object
    fingerprint: str
    context: AIContext
    from_cache: bool
    usage: dict[str, int]


def _run(
    *,
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    client: AIClient | None,
    cache: AICache | None,
    operation: str,
    builder: Callable[[AIContext], list[dict[str, str]]],
    model: type,
) -> InsightResult:
    context = build_ai_context(dataset, calculation)
    store = cache if cache is not None else default_cache()
    key = AICache.make_key(context.fingerprint, operation)

    cached = store.get(key)
    if cached is not None:
        return InsightResult(
            value=cached[0],
            fingerprint=context.fingerprint,
            context=context,
            from_cache=True,
            usage=cached[1],
        )

    active = client or AIClient()
    completion = active.chat(builder(context), json_mode=True)
    validated = validate_response(model, completion.content)
    usage = completion.usage.as_dict
    store.put(key, (validated, usage))
    return InsightResult(
        value=validated,
        fingerprint=context.fingerprint,
        context=context,
        from_cache=False,
        usage=usage,
    )


def generate_inventory_insights(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    client: AIClient | None = None,
    cache: AICache | None = None,
) -> InsightResult:
    """Interpret the current inventory position, risks and actions."""

    return _run(
        dataset=dataset,
        calculation=calculation,
        client=client,
        cache=cache,
        operation=OPERATION_INVENTORY,
        builder=inventory_insights_messages,
        model=InventoryInsightResponse,
    )


def generate_consumption_insights(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    client: AIClient | None = None,
    cache: AICache | None = None,
) -> InsightResult:
    """Analyse the consumption pattern for the report date."""

    return _run(
        dataset=dataset,
        calculation=calculation,
        client=client,
        cache=cache,
        operation=OPERATION_CONSUMPTION,
        builder=consumption_insights_messages,
        model=ConsumptionInsightResponse,
    )


def explain_replenishment(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    client: AIClient | None = None,
    cache: AICache | None = None,
) -> InsightResult:
    """Explain why an order is or is not required."""

    return _run(
        dataset=dataset,
        calculation=calculation,
        client=client,
        cache=cache,
        operation=OPERATION_REPLENISHMENT,
        builder=replenishment_messages,
        model=ReplenishmentExplanation,
    )
