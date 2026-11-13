"""Natural-language inventory analyst.

The analyst answers a planner's question from the supplied engine context. The
question is user text, so it is length-capped and treated as a question rather
than an instruction: the system prompt forbids the model from following
directives that arrive inside the question.

Answers are cached per question text so re-running the same question on the
same dataset and report date never spends another API call.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.cache import AICache, default_cache
from ai.client import AIClient
from ai.context_builder import AIContext, build_ai_context
from ai.prompts import analyst_messages
from ai.schemas import AnalystAnswer, validate_response
from core.models import InventoryCalculation, InventoryDataset

OPERATION_ANALYST = "analyst-question"
MAX_QUESTION_LENGTH = 400

SUGGESTED_QUESTIONS: tuple[str, ...] = (
    "What is my current inventory position?",
    "Why is replenishment not required?",
    "How many days of stock do I have?",
    "What are my biggest inventory risks?",
    "How do open purchase orders affect inventory?",
    "Are there unusual consumption patterns?",
    "Why is the suggested order quantity zero?",
)


@dataclass(frozen=True)
class AnalystResult:
    """A validated answer with its provenance."""

    answer: AnalystAnswer
    fingerprint: str
    context: AIContext
    from_cache: bool
    usage: dict[str, int]
    question: str


def normalise_question(question: str) -> str:
    """Collapse whitespace and enforce the length cap."""

    text = " ".join(str(question or "").split())
    if not text:
        raise ValueError("A question is required.")
    return text[:MAX_QUESTION_LENGTH]


def answer_question(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    question: str,
    *,
    client: AIClient | None = None,
    cache: AICache | None = None,
) -> AnalystResult:
    """Answer ``question`` from the engine context, cached per question."""

    normalised = normalise_question(question)
    context = build_ai_context(dataset, calculation)
    store = cache if cache is not None else default_cache()
    key = AICache.make_key(
        context.fingerprint,
        OPERATION_ANALYST,
        question=normalised.lower(),
    )

    cached = store.get(key)
    if cached is not None:
        return AnalystResult(
            answer=cached[0],
            fingerprint=context.fingerprint,
            context=context,
            from_cache=True,
            usage=cached[1],
            question=normalised,
        )

    active = client or AIClient()
    completion = active.chat(analyst_messages(context, normalised), json_mode=True)
    validated = validate_response(AnalystAnswer, completion.content)
    usage = completion.usage.as_dict
    store.put(key, (validated, usage))
    return AnalystResult(
        answer=validated,
        fingerprint=context.fingerprint,
        context=context,
        from_cache=False,
        usage=usage,
        question=normalised,
    )
