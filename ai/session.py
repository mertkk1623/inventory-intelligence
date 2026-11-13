"""Session-scoped AI cache for the Streamlit UI.

The cache lives in ``st.session_state`` rather than at module level, so one
browser session never sees another session's AI answers. It survives Streamlit
reruns, which is what prevents a rerun from spending another API request.

Only successful, schema-validated results are stored here.
"""

from __future__ import annotations

import streamlit as st

from ai.cache import AICache
from ai.context_builder import build_ai_context
from core.models import InventoryCalculation, InventoryDataset

AI_STORE_KEY = "ii_ai_store"


def session_cache() -> AICache:
    """Return the AI cache bound to the current Streamlit session."""

    store = st.session_state.get(AI_STORE_KEY)
    if not isinstance(store, AICache):
        store = AICache()
        st.session_state[AI_STORE_KEY] = store
    return store


def clear_ai_state() -> None:
    """Drop every cached AI result from the session."""

    st.session_state.pop(AI_STORE_KEY, None)


def current_fingerprint(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> str:
    """Return the cache fingerprint for the active dataset and report date."""

    return build_ai_context(dataset, calculation).fingerprint
