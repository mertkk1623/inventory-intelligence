"""Pydantic models that validate every structured AI response.

The model is asked for JSON. Nothing is trusted until it has passed through
these models, so a malformed or unexpected payload becomes a clean
:class:`~ai.errors.AIResponseError` instead of leaking into the UI.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ai.errors import AIResponseError

MAX_TEXT_LENGTH = 1200
MAX_ITEM_LENGTH = 400
# The model sometimes returns a couple more list items than a tight schema
# allows. Rejecting the whole answer for one extra supporting-data line is
# unhelpful, so the ceiling is generous and the prompt asks for brevity.
MAX_LIST_ITEMS = 15


class _StrictModel(BaseModel):
    """Reject unknown keys so a drifting prompt cannot silently pass."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _clean_text(value: str, *, limit: int = MAX_TEXT_LENGTH) -> str:
    text = " ".join(str(value).split())
    if not text:
        raise ValueError("Text fields must not be empty.")
    return text[:limit]


class Finding(_StrictModel):
    """One observation backed by engine values."""

    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("title", "detail")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value)


class Risk(_StrictModel):
    """A risk with the data that supports it."""

    title: str = Field(min_length=1, max_length=120)
    severity: str = Field(default="medium", max_length=20)
    detail: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("title", "detail")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("severity")
    @classmethod
    def _normalise_severity(cls, value: str) -> str:
        lowered = _clean_text(value, limit=20).lower()
        return lowered if lowered in {"low", "medium", "high"} else "medium"


class ActionSuggestion(_StrictModel):
    """A recommendation that always carries evidence and a limitation."""

    finding: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    supporting_data: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    suggested_action: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    confidence: str = Field(default="medium", max_length=20)
    limitation: str = Field(default="", max_length=MAX_TEXT_LENGTH)

    @field_validator(
        "finding",
        "supporting_data",
        "suggested_action",
        "reason",
        "limitation",
    )
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value) if value.strip() else ""

    @field_validator("confidence")
    @classmethod
    def _normalise_confidence(cls, value: str) -> str:
        lowered = _clean_text(value, limit=20).lower()
        return lowered if lowered in {"low", "medium", "high"} else "medium"


class InventoryInsightResponse(_StrictModel):
    """Narrative overview plus findings, risks and evidence-backed actions."""

    overview: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    findings: list[Finding] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    risks: list[Risk] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    actions: list[ActionSuggestion] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    limitations: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)

    @field_validator("overview")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("limitations")
    @classmethod
    def _normalise_limitations(cls, value: list[str]) -> list[str]:
        return [_clean_text(item) for item in value if item.strip()]


class ConsumptionInsightResponse(_StrictModel):
    """Consumption pattern analysis."""

    summary: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    patterns: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    highest_day_note: str = Field(default="", max_length=MAX_ITEM_LENGTH)
    lowest_day_note: str = Field(default="", max_length=MAX_ITEM_LENGTH)
    zero_consumption_note: str = Field(default="", max_length=MAX_ITEM_LENGTH)
    risks: list[Risk] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)

    @field_validator("summary")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("patterns")
    @classmethod
    def _normalise_patterns(cls, value: list[str]) -> list[str]:
        return [_clean_text(item) for item in value if item.strip()]


class ReplenishmentExplanation(_StrictModel):
    """Why an order is or is not required, with the supporting arithmetic."""

    decision: str = Field(min_length=1, max_length=60)
    explanation: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    supporting_data: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    caveats: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)

    @field_validator("decision", "explanation")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("supporting_data", "caveats")
    @classmethod
    def _normalise_lists(cls, value: list[str]) -> list[str]:
        return [_clean_text(item) for item in value if item.strip()]


class AnalystAnswer(_StrictModel):
    """A natural-language answer with its evidence and limitations."""

    answer: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    supporting_data: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    limitations: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)

    @field_validator("answer")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("supporting_data", "limitations")
    @classmethod
    def _normalise_lists(cls, value: list[str]) -> list[str]:
        return [_clean_text(item) for item in value if item.strip()]


def parse_json_object(raw: str) -> dict[str, Any]:
    """Decode a JSON object, tolerating a fenced code block."""

    text = (raw or "").strip()
    if not text:
        raise AIResponseError("The AI provider returned an empty response.")

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        truncated = not text.rstrip().endswith(("}", "]"))
        hint = (
            " The response looks truncated, which usually means the token "
            "ceiling was reached before the JSON was complete."
            if truncated
            else ""
        )
        raise AIResponseError(
            f"The AI provider did not return valid JSON.{hint}"
        ) from exc

    if not isinstance(payload, dict):
        raise AIResponseError("The AI provider returned JSON that is not an object.")
    return payload


def validate_response(model: type[BaseModel], raw: str):
    """Parse and validate ``raw`` against ``model``."""

    payload = parse_json_object(raw)
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ())) or "response"
        message = first.get("msg", "invalid value")
        raise AIResponseError(
            f"The AI response did not match the expected schema at "
            f"'{location}': {message}"
        ) from exc
