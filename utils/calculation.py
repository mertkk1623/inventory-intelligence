"""Central calculation access for the Streamlit UI.

Every analytics screen receives the same :class:`InventoryCalculation`
instance from this module. The UI never re-implements stock, consumption or
replenishment formulas.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from core.calculations import calculate_inventory
from core.models import InventoryCalculation, InventoryDataset
from utils.session_state import CALCULATION_KEY, CALCULATION_SIGNATURE_KEY


def get_calculation(
    dataset: InventoryDataset,
    report_date: date,
) -> InventoryCalculation:
    """Return the shared calculation result for a dataset and report date.

    The result is cached in session state and invalidated automatically when
    the dataset or report date changes. This keeps every screen on exactly
    the same result object during a script run.
    """

    signature = (dataset, report_date)
    cached = st.session_state.get(CALCULATION_KEY)
    if (
        isinstance(cached, InventoryCalculation)
        and st.session_state.get(CALCULATION_SIGNATURE_KEY) == signature
    ):
        return cached

    calculation = calculate_inventory(dataset, report_date)
    st.session_state[CALCULATION_KEY] = calculation
    st.session_state[CALCULATION_SIGNATURE_KEY] = signature
    return calculation
