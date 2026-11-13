"""Report context: one engine result reshaped for Excel and PDF output.

Both report formats consume this module, so a report can never disagree with
the dashboard or with the other format. No inventory, consumption or
replenishment value is calculated here; every number originates from the
Package 2 engine or from the zero-filled series in ``analytics.series``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from analytics.series import (
    ConsumptionSummary,
    DailyConsumption,
    OpenOrderRow,
    WeeklyConsumption,
    consumption_summary,
    daily_consumption_series,
    open_order_rows,
    stock_balance_series,
    weekly_consumption_series,
)
from core.models import (
    InventoryCalculation,
    InventoryDataset,
    ProductMaster,
)


@dataclass(frozen=True)
class ReportContext:
    """Everything a report needs, derived once from the shared calculation."""

    dataset: InventoryDataset
    calculation: InventoryCalculation
    generated_at: datetime
    balance_points: tuple[tuple[date, int], ...]
    daily: tuple[DailyConsumption, ...]
    weekly: tuple[WeeklyConsumption, ...]
    summary: ConsumptionSummary
    open_orders: tuple[OpenOrderRow, ...]

    @property
    def product(self) -> ProductMaster:
        return self.dataset.product

    @property
    def unit(self) -> str:
        return self.dataset.product.unit

    @property
    def report_date(self) -> date:
        return self.calculation.report_date

    @property
    def is_historical(self) -> bool:
        return self.calculation.is_historical_report

    @property
    def consumption_start(self) -> date | None:
        return self.daily[0].day if self.daily else None

    @property
    def consumption_end(self) -> date | None:
        return self.daily[-1].day if self.daily else None

    @property
    def source_label(self) -> str:
        return "Demo dataset" if self.dataset.is_demo else "Uploaded workbook"

    @property
    def report_type_label(self) -> str:
        return "Historical report" if self.is_historical else "Current report"

    @property
    def file_stem(self) -> str:
        code = _safe_token(self.product.product_code)
        return f"inventory-intelligence_{code}_{self.report_date.isoformat()}"

    def closing_balance(self, day: date) -> int | None:
        """Return the engine closing balance for ``day``, if available."""

        for point_day, balance in self.balance_points:
            if point_day == day:
                return balance
        return None

    def movement_rows(self) -> tuple[tuple[date, str, int, str, int | None], ...]:
        """Return report-ordered movement rows with the engine balance.

        Rows are oldest first so the sheet reads like a ledger. The balance is
        the engine's closing balance for the movement date; on dates with more
        than one movement, every row shows that date's closing balance.
        """

        rows = [
            movement
            for movement in self.dataset.movements
            if movement.date <= self.report_date
        ]
        rows.sort(key=lambda movement: movement.date)
        return tuple(
            (
                movement.date,
                movement.transaction_type,
                int(movement.quantity),
                movement.description,
                self.closing_balance(movement.date),
            )
            for movement in rows
        )

    @property
    def notes(self) -> tuple[str, ...]:
        """Methodology and limitation notes shared by both report formats."""

        calculation = self.calculation
        notes: list[str] = [
            (
                "Current Stock = Opening Stock + Total IN - Total OUT, counting "
                "only movements on or before the report date."
            ),
            (
                "Average Daily Consumption = OUT quantity in the consumption "
                "window divided by the covered calendar days. Days without an OUT "
                "movement still count, up to a maximum of 30 days."
            ),
            (
                "Days of Supply = Current Stock / Average Daily Consumption. It "
                "is not reported when consumption is zero."
            ),
            "Reorder Point = Average Daily Consumption x Lead Time + Safety Stock.",
            (
                "Target Stock = Average Daily Consumption x (Lead Time + Target "
                "Coverage) + Safety Stock."
            ),
            (
                "Suggested Order Quantity = ceil(Target Stock - Inventory "
                "Position) when Inventory Position is at or below the Reorder "
                "Point; otherwise 0."
            ),
        ]

        if calculation.replenishment_supported:
            notes.append(
                "Inventory Position = Current Stock + all open order quantities. "
                "Open orders are incoming supply and are never added to Current "
                "Stock."
            )
            notes.append(
                "Overdue orders are open orders whose expected delivery date is "
                "before the report date."
            )
        else:
            notes.append(
                "Historical reports show descriptive stock and consumption "
                "metrics only. Current open orders are excluded from Inventory "
                "Position and no order suggestion is produced."
            )

        if calculation.negative_stock_warning:
            notes.append(
                f"Negative stock warning: the running balance fell to "
                f"{calculation.lowest_stock_balance:,} {self.unit}. The balance "
                "is reported without clamping."
            )

        if not self.open_orders:
            notes.append("This dataset contains no open purchase orders.")

        return tuple(notes)


def build_report_context(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
    *,
    generated_at: datetime | None = None,
) -> ReportContext:
    """Assemble the report context from the shared calculation result.

    ``calculation`` must be the object produced by ``calculate_inventory`` for
    ``dataset`` and its report date; the function verifies that so a report can
    never be built from mismatched inputs.
    """

    if not isinstance(dataset, InventoryDataset):
        raise TypeError("A validated InventoryDataset is required for reporting.")
    if not isinstance(calculation, InventoryCalculation):
        raise TypeError("The calculation engine result is required for reporting.")

    product = dataset.product
    if product.opening_stock_date > calculation.report_date:
        raise ValueError(
            "The report date is before the opening stock date; this dataset has "
            "no reportable history."
        )

    daily = daily_consumption_series(dataset, calculation.report_date)
    return ReportContext(
        dataset=dataset,
        calculation=calculation,
        generated_at=generated_at or datetime.now(),
        balance_points=stock_balance_series(dataset, calculation.report_date),
        daily=daily,
        weekly=weekly_consumption_series(daily),
        summary=consumption_summary(daily),
        open_orders=open_order_rows(dataset, calculation.report_date),
    )


def _safe_token(value: str) -> str:
    """Reduce a product code to a file-name-safe token."""

    token = "".join(
        character if character.isalnum() or character in ("-", "_") else "-"
        for character in value
    ).strip("-")
    return token or "product"
