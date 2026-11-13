"""Professional Plotly figures for the analytics screens.

Every label, annotation and hover template is resolved through
:mod:`utils.i18n`, so the charts follow the selected interface language while
the underlying series stay unchanged.
"""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go

from analytics.series import (
    DailyConsumption,
    WeeklyConsumption,
)
from core.models import InventoryCalculation
from utils.i18n import chart_date_formats, format_number, t

PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SUCCESS = "#16A36A"
WARNING = "#D97706"
CRITICAL = "#DC4444"
NAVY = "#14243A"
MUTED = "#64748B"
GRID = "#EEF2F7"
AXIS = "#E4E9F0"

_FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def _style(
    figure: go.Figure,
    *,
    height: int,
    y_title: str = "",
    showlegend: bool = False,
) -> go.Figure:
    tick_format, hover_format = chart_date_formats()
    figure.update_layout(
        height=height,
        margin=dict(l=6, r=12, t=22, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=11, color="#475569"),
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor=AXIS,
            font=dict(family=_FONT, size=11, color="#0F172A"),
        ),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=AXIS,
            linewidth=1,
            tickfont=dict(size=10, color=MUTED),
            tickformat=tick_format,
            hoverformat=hover_format,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRID,
            zeroline=False,
            linecolor=AXIS,
            tickfont=dict(size=10, color=MUTED),
            title=dict(
                text=y_title,
                font=dict(size=10, color=MUTED),
                standoff=8,
            ),
            rangemode="tozero",
        ),
    )
    return figure


def stock_level_figure(
    points: tuple[tuple[date, int], ...],
    calculation: InventoryCalculation,
    *,
    height: int = 300,
    movement_markers: tuple[tuple[date, int, str, int, str], ...] = (),
) -> go.Figure:
    """Stock balance over time with safety stock and reorder point lines."""

    figure = go.Figure()
    if points:
        dates = [point[0] for point in points]
        balances = [point[1] for point in points]
        figure.add_trace(
            go.Scatter(
                x=dates,
                y=balances,
                mode="lines",
                name=t("Stock balance"),
                line=dict(color=PRIMARY, width=2.4, shape="linear"),
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.08)",
                hovertemplate=t(
                    "%{x|%d %b %Y}<br>Balance: %{y:,.0f} units"
                )
                + "<extra></extra>",
            )
        )

        figure.add_trace(
            go.Scatter(
                x=[dates[-1]],
                y=[balances[-1]],
                mode="markers",
                name=t("Current Stock"),
                marker=dict(
                    color=PRIMARY,
                    size=8,
                    line=dict(color="#FFFFFF", width=2),
                ),
                hovertemplate=t(
                    "Current stock<br>%{x|%d %b %Y}<br>%{y:,.0f} units"
                )
                + "<extra></extra>",
            )
        )

    if movement_markers:
        balance_by_day = {day: balance for day, balance in points}
        for transaction_type, color, symbol in (
            ("IN", SUCCESS, "triangle-up"),
            ("OUT", CRITICAL, "triangle-down"),
        ):
            selected = [
                marker for marker in movement_markers if marker[2] == transaction_type
            ]
            if not selected:
                continue
            figure.add_trace(
                go.Scatter(
                    x=[marker[0] for marker in selected],
                    y=[balance_by_day.get(marker[0], marker[1]) for marker in selected],
                    mode="markers",
                    name=transaction_type,
                    marker=dict(color=color, size=9, symbol=symbol),
                    customdata=[
                        [marker[3], marker[4]] for marker in selected
                    ],
                    hovertemplate=(
                        "%{x|" + chart_date_formats()[1] + "}<br>"
                        + transaction_type
                        + " %{customdata[0]:,.0f} "
                        + t("units")
                        + "<br>%{customdata[1]}<extra></extra>"
                    ),
                )
            )

    figure.add_hline(
        y=calculation.safety_stock,
        line_dash="dot",
        line_color=SUCCESS,
        line_width=1.4,
        annotation_text=t(
            "Safety stock {value}",
            value=format_number(calculation.safety_stock),
        ),
        annotation_position="top left",
        annotation_font=dict(size=9, color=SUCCESS),
    )
    figure.add_hline(
        y=float(calculation.reorder_point),
        line_dash="dash",
        line_color=CRITICAL,
        line_width=1.4,
        annotation_text=t(
            "Reorder point {value}",
            value=format_number(round(float(calculation.reorder_point))),
        ),
        annotation_position="bottom left",
        annotation_font=dict(size=9, color=CRITICAL),
    )

    _style(
        figure,
        height=height,
        y_title=t("Units"),
        showlegend=bool(movement_markers),
    )
    return figure


def daily_consumption_figure(
    daily: tuple[DailyConsumption, ...],
    *,
    height: int = 280,
) -> go.Figure:
    """Daily OUT consumption with zero-consumption days preserved."""

    figure = go.Figure()
    if daily:
        figure.add_trace(
            go.Scatter(
                x=[entry.day for entry in daily],
                y=[entry.quantity for entry in daily],
                mode="lines+markers",
                name=t("Daily consumption"),
                line=dict(color=PRIMARY, width=2.2),
                marker=dict(color=PRIMARY, size=4),
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.07)",
                hovertemplate=t(
                    "%{x|%d %b %Y}<br>%{y:,.0f} units consumed"
                )
                + "<extra></extra>",
            )
        )

    if not daily or all(entry.quantity == 0 for entry in daily):
        figure.add_annotation(
            text=t("No OUT movements in this consumption window"),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=12, color=MUTED),
        )

    _style(figure, height=height, y_title=t("Units consumed"))
    return figure


def weekly_consumption_figure(
    weekly: tuple[WeeklyConsumption, ...],
    *,
    height: int = 280,
) -> go.Figure:
    """Weekly OUT consumption as a clean bar chart."""

    figure = go.Figure()
    if weekly:
        show_text = len(weekly) <= 12
        figure.add_trace(
            go.Bar(
                x=[entry.week_start for entry in weekly],
                y=[entry.quantity for entry in weekly],
                name=t("Weekly consumption"),
                marker=dict(color=PRIMARY, line=dict(color=PRIMARY_DARK, width=1)),
                text=(
                    [
                        format_number(entry.quantity) if entry.quantity else ""
                        for entry in weekly
                    ]
                    if show_text
                    else None
                ),
                textposition="outside",
                cliponaxis=False,
                hovertemplate=t(
                    "Week of %{x|%d %b %Y}<br>%{y:,.0f} units"
                )
                + "<extra></extra>",
            )
        )

    if not weekly or all(entry.quantity == 0 for entry in weekly):
        figure.add_annotation(
            text=t("No consumption recorded in these weeks"),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=12, color=MUTED),
        )

    _style(figure, height=height, y_title=t("Units consumed"))
    figure.update_layout(bargap=0.35)
    return figure


def safety_vs_reorder_figure(
    calculation: InventoryCalculation,
    *,
    height: int = 300,
) -> go.Figure:
    """Compare Safety Stock with the calculated Reorder Point."""

    reorder_point = float(calculation.reorder_point)
    figure = go.Figure(
        go.Bar(
            y=[t("Safety Stock"), t("Reorder Point")],
            x=[calculation.safety_stock, reorder_point],
            orientation="h",
            marker=dict(color=[SUCCESS, CRITICAL]),
            text=[
                format_number(calculation.safety_stock),
                format_number(reorder_point),
            ],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=t("%{y}<br>%{x:,.0f} units") + "<extra></extra>",
        )
    )
    figure.add_vline(
        x=calculation.current_stock,
        line_dash="dot",
        line_color=PRIMARY,
        line_width=1.4,
        annotation_text=t(
            "Current stock {value}",
            value=format_number(calculation.current_stock),
        ),
        annotation_position="top",
        annotation_font=dict(size=9, color=PRIMARY),
    )
    _style(figure, height=height)
    figure.update_xaxes(showgrid=True, gridcolor=GRID, rangemode="tozero")
    figure.update_yaxes(showgrid=False, linecolor=AXIS, tickfont=dict(size=10))
    return figure
