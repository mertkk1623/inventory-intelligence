"""AI Analyst screen.

The screen separates deterministic engine values from AI interpretation. Every
number shown in the "Supporting Data" panel comes straight from the shared
:class:`~core.models.InventoryCalculation`; the model only writes prose about
those numbers.

API calls happen only on an explicit click. Every successful result is cached in
session state by context fingerprint, so a Streamlit rerun never repeats a
request and the same question is never billed twice.

Model output itself is always English: the prompt asks for English prose and the
answer is rendered verbatim. Only the surrounding interface is translated, and
the screen states that scope so a Turkish interface is never surprising.
"""

from __future__ import annotations

import logging
from html import escape

import streamlit as st

from ai.cache import AICache
from ai.client import AIClient
from ai.context_builder import AIContext, build_ai_context
from ai.errors import AIError
from ai.insights import (
    OPERATION_CONSUMPTION,
    OPERATION_INVENTORY,
    OPERATION_REPLENISHMENT,
    explain_replenishment,
    generate_consumption_insights,
    generate_inventory_insights,
)
from ai.inventory_analyst import (
    OPERATION_ANALYST,
    SUGGESTED_QUESTIONS,
    answer_question,
    normalise_question,
)
from ai.schemas import AnalystAnswer
from ai.session import session_cache
from ai.settings import AISettings, load_settings
from components.analytics_ui import (
    KpiItem,
    format_date,
    format_days,
    format_decimal,
    format_quantity,
    kpi_cards,
    page_header,
)
from components.ui import banner, icon, section_header
from core.models import InventoryCalculation, InventoryDataset
from utils.i18n import format_number, t

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "AI-generated interpretations are decision-support suggestions and must be "
    "reviewed by a human."
)

OPERATION_LAST_ANSWER = "last-answer"

SEVERITY_LABEL = {"low": "Low", "medium": "Medium", "high": "High"}


def render_ai_analyst(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    settings: AISettings | None = None,
    cache: AICache | None = None,
) -> None:
    """Render the AI Analyst screen for the active dataset."""

    st.markdown(
        page_header(
            t("AI Analyst"),
            t(
                "AI interpretations of the deterministic calculation result. "
                "The engine owns every number; the model explains what those "
                "numbers mean."
            ),
            dataset,
            as_of=calculation.report_date,
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        banner(
            "info",
            t("Decision support, not automated planning"),
            t(DISCLAIMER),
        ),
        unsafe_allow_html=True,
    )

    try:
        context = build_ai_context(dataset, calculation)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Could not build the AI context")
        st.error(
            t(
                "The AI context could not be prepared. Details: {error}",
                error=exc,
            )
        )
        return

    resolved = settings or load_settings()
    store = cache if cache is not None else session_cache()
    client = AIClient(resolved)
    available = resolved.is_configured

    st.markdown(_status_strip(resolved, context, available), unsafe_allow_html=True)

    if context.is_historical:
        st.markdown(
            banner(
                "warning",
                t("Historical report date"),
                t(
                    "Replenishment planning is not supported for a historical "
                    "report date. The AI layer is told about this limitation "
                    "and will not produce an order quantity."
                ),
            ),
            unsafe_allow_html=True,
        )

    _render_supporting_data(dataset, calculation)

    if not available:
        st.markdown(
            banner(
                "warning",
                t("AI unavailable"),
                t(
                    "No API key is configured, so only the deterministic values "
                    "above are shown. Add AI_API_KEY to .streamlit/secrets.toml "
                    "or set the DEPLOY_API_KEY environment variable to enable AI "
                    "interpretation."
                ),
            ),
            unsafe_allow_html=True,
        )
        return

    _render_insight_sections(
        dataset, calculation, context=context, client=client, store=store
    )
    _render_question_section(
        dataset, calculation, context=context, client=client, store=store
    )


# ---------------------------------------------------------------------------
# Deterministic values
# ---------------------------------------------------------------------------


def _render_supporting_data(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    """Show the engine values the AI is allowed to reference."""

    product = dataset.product
    unit = product.unit

    st.markdown(
        section_header(
            t("01 · Deterministic input"),
            t("Supporting data"),
            t(
                "Every value below is produced by the calculation engine. These "
                "are the only numbers the AI is allowed to cite."
            ),
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Current Stock"),
                    format_quantity(calculation.current_stock, unit),
                    t("Opening + IN − OUT up to the report date"),
                    "critical" if calculation.negative_stock_warning else "",
                ),
                KpiItem(
                    t("Average Daily Consumption"),
                    format_decimal(
                        calculation.average_daily_consumption, unit, places=2
                    ),
                    t(
                        "{days} calendar days",
                        days=calculation.consumption_coverage_days,
                    ),
                ),
                KpiItem(
                    t("Days of Supply"),
                    format_days(calculation.days_of_supply),
                    t("Current stock / average consumption"),
                ),
                KpiItem(
                    t("Safety Stock"),
                    format_quantity(calculation.safety_stock, unit),
                    t("Minimum planning buffer"),
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Reorder Point"),
                    format_decimal(calculation.reorder_point, unit, places=1),
                    t("Average consumption × lead time + safety stock"),
                ),
                KpiItem(
                    t("Inventory Position"),
                    format_quantity(calculation.inventory_position, unit),
                    t("Current stock + open orders")
                    if calculation.replenishment_supported
                    else t("Current stock only (historical report)"),
                ),
                KpiItem(
                    t("Open Purchase Orders"),
                    "—"
                    if not calculation.replenishment_supported
                    else format_quantity(
                        calculation.total_open_order_quantity, unit
                    ),
                    t("Incoming supply, never added to current stock"),
                    "muted" if not calculation.replenishment_supported else "",
                ),
                KpiItem(
                    t("Suggested Order"),
                    "—"
                    if not calculation.replenishment_supported
                    else format_quantity(
                        calculation.suggested_order_quantity, unit
                    ),
                    t("Not generated for historical reports")
                    if not calculation.replenishment_supported
                    else t("No reorder required")
                    if not calculation.reorder_required
                    else t("Order up to target stock"),
                    "muted"
                    if not calculation.replenishment_supported
                    else "success"
                    if not calculation.reorder_required
                    else "warning",
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    detail_rows = [
        (t("Report date"), format_date(calculation.report_date)),
        (t("Product"), f"{product.product_code} · {product.product_name}"),
        (t("Unit of measure"), unit),
        (
            t("Target stock"),
            format_decimal(calculation.target_stock, unit, places=1),
        ),
        (
            t("Overdue orders"),
            "—"
            if not calculation.replenishment_supported
            else format_number(calculation.overdue_order_count),
        ),
        (
            t("Movements in range"),
            t(
                "{count} in workbook",
                count=format_number(dataset.movement_count),
            ),
        ),
    ]
    cells = "".join(
        f'<div class="ii-detail"><div class="ii-detail-label">{escape(label)}</div>'
        f'<div class="ii-detail-value">{escape(value)}</div></div>'
        for label, value in detail_rows
    )
    st.markdown(f'<div class="ii-detail-grid">{cells}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# AI insight sections
# ---------------------------------------------------------------------------


def _render_insight_sections(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    context: AIContext,
    client: AIClient,
    store: AICache,
) -> None:
    st.markdown(
        section_header(
            t("02 · AI interpretation"),
            t("AI Inventory Overview"),
            t(
                "Generated from the values above. Nothing here changes the "
                "engine result."
            ),
        ),
        unsafe_allow_html=True,
    )

    key = AICache.make_key(context.fingerprint, OPERATION_INVENTORY)
    cached = store.get(key)
    overview = cached[0] if cached is not None else None

    left, right = st.columns([1, 3], gap="medium")
    with left:
        generate = st.button(
            t("Regenerate") if overview is not None else t("Generate AI overview"),
            icon=":material/auto_awesome:",
            type="primary",
            width="stretch",
            key=f"ai_generate_overview_{context.fingerprint}",
        )
    with right:
        st.caption(
            t("Reusing the cached result for this dataset and report date.")
            if overview is not None
            else t(
                "One API request is sent for this dataset and report date, then "
                "cached."
            )
        )

    if generate:
        try:
            outcome = generate_inventory_insights(
                dataset, calculation, client=client, cache=store
            )
        except AIError as exc:
            _report_error(exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Unexpected AI failure")
            st.error(
                t(
                    "The AI analysis failed unexpectedly. Details: {error}",
                    error=exc,
                )
            )
        else:
            overview = outcome.value
            st.caption(
                t(
                    "Generated just now · {tokens} tokens",
                    tokens=format_number(outcome.usage.get("total_tokens", 0)),
                )
                if not outcome.from_cache
                else t("Served from cache · no API request was sent.")
            )

    if overview is None:
        st.markdown(
            '<div class="ii-empty">'
            f'<div class="ii-empty-title">{escape(t("No AI interpretation yet"))}'
            "</div>"
            f'<div class="ii-empty-text">'
            f"{escape(t('The deterministic values above are complete on their own. Generate an AI overview to add narrative findings, risks and suggested actions.'))}"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        _render_overview(overview)
        _render_findings(overview)
        _render_risks(overview)
        _render_actions(overview)

    _render_optional_insights(
        dataset, calculation, context=context, client=client, store=store
    )


def _render_overview(result) -> None:
    limitations = ""
    if result.limitations:
        items = "".join(f"<li>{escape(item)}</li>" for item in result.limitations)
        limitations = (
            f'<div class="ii-ai-limits"><strong>{escape(t("Limitations"))}'
            f"</strong><ul>{items}</ul></div>"
        )
    st.markdown(
        f'<div class="ii-ai-card">'
        f'<div class="ii-ai-card-kicker">{icon("sparkle", 14)} '
        f"{escape(t('AI overview'))}</div>"
        f'<p class="ii-ai-prose">{escape(result.overview)}</p>'
        f"{limitations}"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_findings(result) -> None:
    if not result.findings:
        return
    st.markdown(
        section_header(t("03 · AI interpretation"), t("Key Findings")),
        unsafe_allow_html=True,
    )
    rows = "".join(
        '<div class="ii-ai-finding">'
        f'<div class="ii-ai-finding-title">{escape(finding.title)}</div>'
        f'<div class="ii-ai-finding-text">{escape(finding.detail)}</div>'
        "</div>"
        for finding in result.findings
    )
    st.markdown(f'<div class="ii-ai-list">{rows}</div>', unsafe_allow_html=True)


def _render_risks(result) -> None:
    if not result.risks:
        return
    st.markdown(
        section_header(t("04 · AI interpretation"), t("Inventory Risks")),
        unsafe_allow_html=True,
    )
    rows = "".join(
        '<div class="ii-ai-risk">'
        '<div class="ii-ai-risk-head">'
        f'<span class="ii-ai-risk-title">{escape(risk.title)}</span>'
        f'<span class="ii-ai-sev {escape(risk.severity)}">'
        f"{escape(_severity(risk.severity))}</span>"
        "</div>"
        f'<div class="ii-ai-risk-text">{escape(risk.detail)}</div>'
        "</div>"
        for risk in result.risks
    )
    st.markdown(f'<div class="ii-ai-list">{rows}</div>', unsafe_allow_html=True)


def _render_actions(result) -> None:
    if not result.actions:
        return
    st.markdown(
        section_header(
            t("05 · AI interpretation"),
            t("Recommended Actions"),
            t(
                "Each suggestion carries its finding, supporting data, reason, "
                "confidence and limitation."
            ),
        ),
        unsafe_allow_html=True,
    )
    cards = "".join(
        '<div class="ii-ai-action">'
        '<div class="ii-ai-action-head">'
        f'<span class="ii-ai-action-title">{escape(action.suggested_action)}</span>'
        f'<span class="ii-ai-sev {escape(action.confidence)}">'
        f"{escape(_severity(action.confidence))}</span>"
        "</div>"
        '<dl class="ii-ai-fields">'
        f"<dt>{escape(t('Finding'))}</dt><dd>{escape(action.finding)}</dd>"
        f"<dt>{escape(t('Supporting data'))}</dt>"
        f"<dd>{escape(action.supporting_data)}</dd>"
        f"<dt>{escape(t('Reason'))}</dt><dd>{escape(action.reason)}</dd>"
        f"<dt>{escape(t('Confidence'))}</dt>"
        f"<dd>{escape(_severity(action.confidence))}</dd>"
        f"<dt>{escape(t('Limitation'))}</dt>"
        f"<dd>{escape(action.limitation or t('Not stated.'))}</dd>"
        "</dl>"
        "</div>"
        for action in result.actions
    )
    st.markdown(f'<div class="ii-ai-actions">{cards}</div>', unsafe_allow_html=True)


def _render_optional_insights(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    context: AIContext,
    client: AIClient,
    store: AICache,
) -> None:
    st.markdown(
        section_header(
            t("06 · AI interpretation"),
            t("Consumption and replenishment"),
            t(
                "Two optional analyses. Each spends one API request and is "
                "cached afterwards."
            ),
        ),
        unsafe_allow_html=True,
    )

    consumption_key = AICache.make_key(context.fingerprint, OPERATION_CONSUMPTION)
    replenishment_key = AICache.make_key(
        context.fingerprint, OPERATION_REPLENISHMENT
    )
    has_consumption = consumption_key in store
    has_replenishment = replenishment_key in store

    left, right = st.columns(2, gap="medium")
    with left:
        if st.button(
            t("Regenerate consumption analysis")
            if has_consumption
            else t("Analyse consumption"),
            icon=":material/query_stats:",
            width="stretch",
            key=f"ai_generate_consumption_{context.fingerprint}",
        ):
            try:
                generate_consumption_insights(
                    dataset, calculation, client=client, cache=store
                )
            except AIError as exc:
                _report_error(exc)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Unexpected consumption insight failure")
                st.error(
                    t(
                        "The consumption analysis failed. Details: {error}",
                        error=exc,
                    )
                )
    with right:
        if st.button(
            t("Regenerate replenishment explanation")
            if has_replenishment
            else t("Explain replenishment"),
            icon=":material/inventory_2:",
            width="stretch",
            key=f"ai_generate_replenishment_{context.fingerprint}",
        ):
            try:
                explain_replenishment(
                    dataset, calculation, client=client, cache=store
                )
            except AIError as exc:
                _report_error(exc)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Unexpected replenishment explanation failure")
                st.error(
                    t(
                        "The replenishment explanation failed. Details: {error}",
                        error=exc,
                    )
                )

    consumption = store.get(consumption_key)
    if consumption is not None:
        _render_consumption(consumption[0])

    replenishment = store.get(replenishment_key)
    if replenishment is not None:
        _render_replenishment(replenishment[0])


def _render_consumption(value) -> None:
    st.markdown(
        f'<div class="ii-ai-card">'
        f'<div class="ii-ai-card-kicker">{icon("query_stats", 14)} '
        f"{escape(t('Consumption Insights'))}</div>"
        f'<p class="ii-ai-prose">{escape(value.summary)}</p>'
        f"{_note_row(t('Peak day'), value.highest_day_note)}"
        f"{_note_row(t('Lowest day'), value.lowest_day_note)}"
        f"{_note_row(t('Zero consumption'), value.zero_consumption_note)}"
        f"{_note_row(t('Patterns'), '; '.join(value.patterns))}"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_replenishment(value) -> None:
    decision = value.decision.replace("-", " ").replace("_", " ").capitalize()
    supporting = "".join(f"<li>{escape(item)}</li>" for item in value.supporting_data)
    caveats = "".join(f"<li>{escape(item)}</li>" for item in value.caveats)
    caveat_block = (
        f'<div class="ii-ai-limits"><strong>{escape(t("Caveats"))}</strong>'
        f"<ul>{caveats}</ul></div>"
        if caveats
        else ""
    )
    st.markdown(
        f'<div class="ii-ai-card">'
        f'<div class="ii-ai-card-kicker">{icon("inventory_2", 14)} '
        f"{escape(t('Replenishment Explanation'))}</div>"
        f'<div class="ii-ai-decision">{escape(decision)}</div>'
        f'<p class="ii-ai-prose">{escape(value.explanation)}</p>'
        f'<div class="ii-ai-limits"><strong>{escape(t("Supporting data"))}'
        f"</strong><ul>{supporting}</ul></div>"
        f"{caveat_block}"
        "</div>",
        unsafe_allow_html=True,
    )


def _note_row(label: str, text: str) -> str:
    if not text:
        return ""
    return (
        f'<div class="ii-ai-note"><span>{escape(label)}</span>{escape(text)}</div>'
    )


# ---------------------------------------------------------------------------
# Natural-language analyst
# ---------------------------------------------------------------------------


def _render_question_section(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    context: AIContext,
    client: AIClient,
    store: AICache,
) -> None:
    st.markdown(
        section_header(
            t("07 · Ask the analyst"),
            t("Natural-language question"),
            t(
                "Ask about the active dataset. Answers are cached per question, "
                "so asking the same thing twice costs nothing."
            ),
        ),
        unsafe_allow_html=True,
    )

    question = st.text_input(
        t("Your question"),
        key=f"ai_question_input_{context.fingerprint}",
        placeholder=t("Why is replenishment not required?"),
        label_visibility="collapsed",
    )

    st.markdown(
        f'<div class="ii-ai-suggest-label">{escape(t("Suggested questions"))}</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(3, gap="small")
    selected: str | None = None
    for index, suggestion in enumerate(SUGGESTED_QUESTIONS[:6]):
        with columns[index % 3]:
            if st.button(
                t(suggestion),
                key=f"ai_suggest_{context.fingerprint}_{index}",
                width="stretch",
            ):
                selected = suggestion

    submitted = st.button(
        t("Ask the analyst"),
        icon=":material/forum:",
        type="primary",
        key=f"ai_ask_{context.fingerprint}",
    )

    if selected is not None:
        _answer(
            dataset,
            calculation,
            question=selected,
            context=context,
            client=client,
            store=store,
        )
    elif submitted:
        try:
            normalised = normalise_question(question)
        except ValueError as exc:
            st.warning(str(exc))
        else:
            _answer(
                dataset,
                calculation,
                question=normalised,
                context=context,
                client=client,
                store=store,
            )

    _render_last_answer(store, context)


def _answer(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    question: str,
    context: AIContext,
    client: AIClient,
    store: AICache,
) -> None:
    try:
        outcome = answer_question(
            dataset, calculation, question, client=client, cache=store
        )
    except AIError as exc:
        _report_error(exc)
        return
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected analyst failure")
        st.error(
            t("The analyst could not answer. Details: {error}", error=exc)
        )
        return

    store.put(
        AICache.make_key(context.fingerprint, OPERATION_LAST_ANSWER),
        (outcome.answer, outcome.question),
    )


def _render_last_answer(store: AICache, context: AIContext) -> None:
    entry = store.get(
        AICache.make_key(context.fingerprint, OPERATION_LAST_ANSWER)
    )
    if entry is None:
        return

    answer, question = entry
    if not isinstance(answer, AnalystAnswer):
        return

    supporting = "".join(
        f"<li>{escape(item)}</li>" for item in answer.supporting_data
    )
    limitations = "".join(
        f"<li>{escape(item)}</li>" for item in answer.limitations
    )
    limitation_block = (
        f'<div class="ii-ai-limits"><strong>{escape(t("Limitations"))}'
        f"</strong><ul>{limitations}</ul></div>"
        if limitations
        else ""
    )
    supporting_block = (
        f'<div class="ii-ai-limits"><strong>{escape(t("Supporting data"))}'
        f"</strong><ul>{supporting}</ul></div>"
        if supporting
        else ""
    )
    st.markdown(
        f'<div class="ii-ai-answer">'
        f'<div class="ii-ai-answer-q">{escape(question)}</div>'
        f'<p class="ii-ai-prose">{escape(answer.answer)}</p>'
        f"{supporting_block}"
        f"{limitation_block}"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _severity(value: str) -> str:
    return t(SEVERITY_LABEL.get(value, "Medium"))


def _report_error(error: AIError) -> None:
    logger.warning("AI request failed: %s", type(error).__name__)
    st.markdown(
        banner(
            "warning",
            t("AI request failed"),
            t(
                "{error} The deterministic values above are unaffected.",
                error=error,
            ),
        ),
        unsafe_allow_html=True,
    )


def _status_strip(
    settings: AISettings,
    context: AIContext,
    available: bool,
) -> str:
    chips = [
        t("Model {model}", model=settings.model),
        t("Provider configured") if available else t("Provider not configured"),
        t("Context {fingerprint}", fingerprint=context.fingerprint[:8]),
        t("Historical report")
        if context.is_historical
        else t("Current report"),
    ]
    if context.untrusted_fields:
        chips.append(t("Untrusted text flagged"))
    return (
        '<div class="ii-report-meta">'
        + "".join(f"<span>{escape(chip)}</span>" for chip in chips)
        + "</div>"
    )


__all__ = ["DISCLAIMER", "OPERATION_ANALYST", "render_ai_analyst"]
