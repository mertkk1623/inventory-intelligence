"""Excel and PDF reporting for Inventory Intelligence.

The package is deliberately independent from Streamlit. It consumes a
validated :class:`~core.models.InventoryDataset` and the single
:class:`~core.models.InventoryCalculation` produced by the calculation engine,
so every report value comes from one authoritative source.
"""

from __future__ import annotations

from reports.report_data import ReportContext, build_report_context

__all__ = ["ReportContext", "build_report_context"]
