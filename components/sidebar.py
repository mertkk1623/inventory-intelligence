"""Sidebar navigation, language switch and workspace status."""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from components.ui import icon
from config import APP_NAME, APP_TAGLINE, APP_VERSION
from utils.i18n import (
    LANGUAGE_NAMES,
    LANGUAGE_WIDGET_KEY,
    format_date,
    get_language,
    set_language,
    t,
)
from utils.session_state import (
    ANALYTICS_PAGES,
    NAV_WIDGET_KEY,
    PAGE_WELCOME,
    PENDING_PAGE_KEY,
    REPORT_DATE_INPUT_KEY,
    REPORT_DATE_SIGNATURE_KEY,
    clear_workspace,
    get_dataset,
    get_page,
    get_report_date,
    report_date_bounds,
    report_date_signature,
    reset_upload_state,
    set_current_page,
    set_report_date,
)


def page_label(page: str) -> str:
    """Return the translated navigation label for a page key."""

    return t(page)


def render_sidebar() -> str:
    """Render the sidebar and return the active page name."""

    dataset = get_dataset()

    with st.sidebar:
        st.markdown(_brand_html(), unsafe_allow_html=True)
        _render_language_switch()

        st.markdown(
            f'<div class="ii-side-label">{escape(t("Workspace"))}</div>',
            unsafe_allow_html=True,
        )

        options = [PAGE_WELCOME]
        if dataset is not None:
            options.extend(ANALYTICS_PAGES)

        previous_page = get_page()

        pending_page = st.session_state.pop(PENDING_PAGE_KEY, None)
        if pending_page in options:
            st.session_state[NAV_WIDGET_KEY] = pending_page
        elif st.session_state.get(NAV_WIDGET_KEY) not in options:
            st.session_state[NAV_WIDGET_KEY] = PAGE_WELCOME

        page = st.radio(
            t("Workspace navigation"),
            options,
            key=NAV_WIDGET_KEY,
            format_func=page_label,
            label_visibility="collapsed",
            width="stretch",
        )

        if page not in options:
            page = PAGE_WELCOME

        if previous_page != PAGE_WELCOME and page == PAGE_WELCOME:
            # Returning to the welcome screen should not keep a stale file
            # selected in the uploader.
            reset_upload_state()

        set_current_page(page)

        if dataset is not None:
            _render_report_date(dataset)

        st.markdown(_status_html(dataset), unsafe_allow_html=True)

        if dataset is not None and st.button(
            t("Clear workspace"),
            icon=":material/delete_outline:",
            width="stretch",
            key="clear_workspace",
        ):
            clear_workspace()
            st.rerun()

        st.markdown(
            f'<div class="ii-side-footer">'
            f"{escape(APP_NAME)} v{escape(APP_VERSION)}<br>"
            f"{escape(t('Single-SKU planning workspace'))}"
            "</div>",
            unsafe_allow_html=True,
        )

    return page or get_page()


def _render_language_switch() -> None:
    """Language selector, kept in session state for the whole session.

    The choice is applied by an ``on_change`` callback. Streamlit runs widget
    callbacks before the script body, so every element renders in the new
    language in the same interaction and no rerun is needed. An explicit
    ``st.rerun()`` here would abort the script before other widgets are
    re-created, and Streamlit 1.53 then discards their state (for example a
    half-typed AI question).
    """

    codes = list(LANGUAGE_NAMES)
    labels = [LANGUAGE_NAMES[code] for code in codes]
    current = get_language()

    st.markdown(
        f'<div class="ii-side-label">{escape(t("Language"))}</div>',
        unsafe_allow_html=True,
    )
    st.selectbox(
        t("Application language"),
        labels,
        index=codes.index(current),
        key=LANGUAGE_WIDGET_KEY,
        label_visibility="collapsed",
        help=t("Language preference is kept for this session."),
        on_change=_apply_language,
    )


def _apply_language() -> None:
    """Callback: switch language and keep the user on the current screen."""

    codes = list(LANGUAGE_NAMES)
    labels = [LANGUAGE_NAMES[code] for code in codes]
    selected = st.session_state.get(LANGUAGE_WIDGET_KEY)
    if selected not in labels:
        return
    set_language(codes[labels.index(selected)])
    # Streamlit 1.53 derives a radio's widget identity from its *formatted*
    # option labels. Because navigation is translated, a language switch
    # creates a new widget id and the selection would fall back to the first
    # option. Re-apply the active page so the user stays where they are.
    st.session_state[PENDING_PAGE_KEY] = get_page()


def _render_report_date(dataset) -> None:
    """Render the shared report-date control below the navigation."""

    signature = report_date_signature(dataset)
    if st.session_state.get(REPORT_DATE_SIGNATURE_KEY) != signature:
        # A new dataset may have a different opening date, so the previous
        # widget value must not leak into the new date range.
        st.session_state.pop(REPORT_DATE_INPUT_KEY, None)
        st.session_state[REPORT_DATE_SIGNATURE_KEY] = signature

    lower, upper = report_date_bounds(dataset)
    current = get_report_date(dataset)

    st.markdown(
        f'<div class="ii-side-label">{escape(t("Report date"))}</div>',
        unsafe_allow_html=True,
    )
    selected = st.date_input(
        t("Report date"),
        value=current,
        min_value=lower,
        max_value=upper,
        format="DD.MM.YYYY" if get_language() == "tr" else "YYYY-MM-DD",
        key=REPORT_DATE_INPUT_KEY,
        label_visibility="collapsed",
        help=t(
            "All calculations use movements up to this date. The earliest "
            "selectable date is the Opening Stock Date."
        ),
    )
    if isinstance(selected, date):
        set_report_date(selected)
        current = selected

    st.markdown(
        f'<div class="ii-side-date-note">'
        f"{escape(t('Calculations use movements up to {date}.', date=format_date(current)))}"
        "</div>",
        unsafe_allow_html=True,
    )


def _brand_html() -> str:
    return (
        '<div class="ii-brand">'
        f'<div class="ii-logo">{icon("layers", 21)}</div>'
        "<div>"
        f'<div class="ii-brand-name">{escape(APP_NAME)}</div>'
        # The tagline is deliberately untranslated, so it stays English even
        # when the interface is Turkish. ``lang="en"`` keeps the stylesheet's
        # ``text-transform: uppercase`` on Latin casing rules instead of
        # turning "Material Planning" into "MATERİAL PLANNİNG".
        f'<div class="ii-brand-sub" lang="en">{escape(t(APP_TAGLINE))}</div>'
        "</div>"
        "</div>"
    )


def _status_html(dataset) -> str:
    if dataset is None:
        return (
            '<div class="ii-side-card muted">'
            f'<div class="ii-side-card-label">{escape(t("No dataset loaded"))}</div>'
            f'<div class="ii-side-card-title">{escape(t("Start from Getting Started"))}</div>'
            f'<div class="ii-side-card-meta">'
            f"{escape(t('Download the template, try the demo, or upload your own workbook.'))}"
            "</div>"
            "</div>"
        )

    source = t("Demo dataset" if dataset.is_demo else "Uploaded workbook")
    return (
        '<div class="ii-side-card">'
        f'<div class="ii-side-card-label">{escape(t("Active dataset"))}</div>'
        f'<div class="ii-side-card-title">{escape(source)}</div>'
        f'<div class="ii-side-card-meta">'
        f"{escape(t('{code} · {movements} movements · {orders} open orders', code=dataset.product.product_code, movements=dataset.movement_count, orders=dataset.open_order_count))}"
        "</div>"
        "</div>"
    )
