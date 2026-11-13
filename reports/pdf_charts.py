"""ReportLab-native charts for the PDF report.

The Streamlit screens use Plotly, which cannot be embedded in a ReportLab
document without a headless browser. These charts therefore draw directly with
``reportlab.graphics.shapes`` from the same zero-filled series the screens use,
so the PDF shows exactly the data behind the dashboard.

Every chart is a self-contained :class:`reportlab.graphics.shapes.Drawing` with
a fixed size, which keeps it inside its frame and prevents page overflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from reportlab.graphics.shapes import (
    Circle,
    Drawing,
    Group,
    Line,
    Polygon,
    PolyLine,
    Rect,
    String,
)

from reports.pdf_theme import (
    CRITICAL,
    FONTS,
    GRID,
    MUTED,
    NAVY,
    PRIMARY,
    PRIMARY_SOFT,
    RULE,
    SUBTLE,
)


@dataclass(frozen=True)
class _Axis:
    left: float
    bottom: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def top(self) -> float:
        return self.bottom + self.height


def _nice_ticks(minimum: float, maximum: float, *, target: int = 4) -> list[float]:
    """Return human-readable axis ticks that cover ``[minimum, maximum]``."""

    if maximum <= minimum:
        maximum = minimum + 1.0
    span = maximum - minimum
    raw_step = span / max(target, 1)
    magnitude = 10.0 ** (len(str(int(abs(raw_step) or 1))) - 1)
    if magnitude <= 0:
        magnitude = 1.0
    normalized = raw_step / magnitude
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        if normalized <= candidate:
            step = candidate * magnitude
            break
    else:  # pragma: no cover - defensive
        step = 10.0 * magnitude

    start = (minimum // step) * step
    ticks: list[float] = []
    value = start
    # A hard cap keeps pathological ranges from producing thousands of ticks.
    while value <= maximum + step * 0.5 and len(ticks) < 12:
        ticks.append(value)
        value += step
    return ticks


def _number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{round(value):,}"
    return f"{value:,.1f}"


def _axis_frame(
    drawing: Drawing,
    *,
    width: float,
    height: float,
    top_pad: float = 10.0,
    bottom_pad: float = 22.0,
    left_pad: float = 40.0,
    right_pad: float = 10.0,
) -> _Axis:
    """Draw the horizontal grid and return the plotting rectangle."""

    axis = _Axis(
        left=left_pad,
        bottom=bottom_pad,
        width=max(width - left_pad - right_pad, 1.0),
        height=max(height - bottom_pad - top_pad, 1.0),
    )
    drawing.add(
        Line(
            axis.left,
            axis.bottom,
            axis.right,
            axis.bottom,
            strokeColor=RULE,
            strokeWidth=0.9,
        )
    )
    return axis


def _y_labels(
    drawing: Drawing,
    axis: _Axis,
    ticks: list[float],
    *,
    minimum: float,
    maximum: float,
) -> None:
    span = maximum - minimum
    for tick in ticks:
        ratio = 0.0 if span <= 0 else (tick - minimum) / span
        y = axis.bottom + ratio * axis.height
        drawing.add(
            Line(
                axis.left,
                y,
                axis.right,
                y,
                strokeColor=GRID if tick > minimum else RULE,
                strokeWidth=0.6,
                strokeDashArray=[2, 3] if tick > minimum else None,
            )
        )
        label = String(
            axis.left - 6,
            y - 2.6,
            _number(tick),
            fontName=FONTS.regular,
            fontSize=6.6,
            fillColor=SUBTLE,
            textAnchor="end",
        )
        drawing.add(label)


def _x_labels(
    drawing: Drawing,
    axis: _Axis,
    labels: list[str],
    *,
    max_labels: int = 7,
) -> None:
    count = len(labels)
    if count == 0:
        return
    step = max(1, (count + max_labels - 1) // max_labels)
    for index in range(0, count, step):
        slot_width = axis.width / count
        x = axis.left + slot_width * (index + 0.5)
        drawing.add(
            String(
                x,
                axis.bottom - 11,
                labels[index],
                fontName=FONTS.regular,
                fontSize=6.6,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )


def _empty_chart(width: float, height: float, message: str) -> Drawing:
    drawing = Drawing(width, height)
    drawing.add(
        Rect(
            0,
            0,
            width,
            height,
            rx=4,
            ry=4,
            fillColor=PRIMARY_SOFT,
            strokeColor=GRID,
            strokeWidth=0.6,
        )
    )
    drawing.add(
        String(
            width / 2,
            height / 2 - 3,
            message,
            fontName=FONTS.regular,
            fontSize=8.2,
            fillColor=MUTED,
            textAnchor="middle",
        )
    )
    return drawing


def _short_day(value: date) -> str:
    return value.strftime("%d %b")


# ---------------------------------------------------------------------------
# Stock balance trend
# ---------------------------------------------------------------------------


def stock_balance_chart(
    points: tuple[tuple[date, int], ...],
    *,
    width: float = 500.0,
    height: float = 168.0,
) -> Drawing:
    """Draw the daily closing stock balance as a filled trend line."""

    if not points:
        return _empty_chart(width, height, "No stock balance history available.")

    values = [float(balance) for _, balance in points]
    lowest = min(values + [0.0])
    highest = max(values + [0.0])
    if highest == lowest:
        highest = lowest + 1.0
    ticks = _nice_ticks(lowest, highest, target=4)
    top = max(ticks[-1], highest)
    bottom = min(ticks[0], lowest)
    span = top - bottom or 1.0

    drawing = Drawing(width, height)
    axis = _axis_frame(drawing, width=width, height=height, left_pad=42.0)
    _y_labels(drawing, axis, ticks, minimum=bottom, maximum=top)

    count = len(points)
    slot = axis.width / max(count - 1, 1)

    def point(index: int, balance: float) -> tuple[float, float]:
        x = axis.left + (slot * index if count > 1 else axis.width / 2)
        y = axis.bottom + ((balance - bottom) / span) * axis.height
        return x, y

    coordinates = [point(index, value) for index, value in enumerate(values)]

    # Area under the curve, anchored on the zero line when it is visible.
    baseline = axis.bottom + ((0.0 - bottom) / span) * axis.height
    baseline = min(max(baseline, axis.bottom), axis.top)
    area_points: list[float] = [coordinates[0][0], baseline]
    for x, y in coordinates:
        area_points.extend([x, y])
    area_points.extend([coordinates[-1][0], baseline])
    drawing.add(
        Polygon(
            area_points,
            fillColor=PRIMARY_SOFT,
            strokeColor=None,
        )
    )

    line: list[float] = []
    for x, y in coordinates:
        line.extend([x, y])
    drawing.add(
        PolyLine(
            line,
            strokeColor=PRIMARY,
            strokeWidth=1.6,
            strokeLineJoin=1,
        )
    )

    # Mark only the report-date point plus the extremes to avoid clutter.
    last_x, last_y = coordinates[-1]
    drawing.add(
        Circle(last_x, last_y, 2.6, fillColor=PRIMARY, strokeColor=None)
    )
    drawing.add(
        String(
            last_x - 3,
            last_y + 7,
            _number(values[-1]),
            fontName=FONTS.bold,
            fontSize=7,
            fillColor=NAVY,
            textAnchor="end",
        )
    )

    if min(values) < 0:
        drawing.add(
            String(
                axis.left,
                axis.top + 3,
                "Negative balance",
                fontName=FONTS.bold,
                fontSize=6.6,
                fillColor=CRITICAL,
            )
        )

    labels = [_short_day(day) for day, _ in points]
    _x_labels(drawing, axis, labels, max_labels=6)
    drawing.add(
        Line(
            axis.left,
            axis.bottom,
            axis.left,
            axis.top,
            strokeColor=RULE,
            strokeWidth=0.9,
        )
    )
    return drawing


# ---------------------------------------------------------------------------
# Consumption bars
# ---------------------------------------------------------------------------


def consumption_chart(
    entries: tuple[tuple[date, int], ...],
    *,
    width: float = 500.0,
    height: float = 138.0,
    bar_color=PRIMARY,
    max_labels: int = 7,
    empty_message: str = "No consumption in this window.",
) -> Drawing:
    """Draw a bar chart for a consumption series (daily or weekly)."""

    if not entries:
        return _empty_chart(width, height, empty_message)

    values = [float(quantity) for _, quantity in entries]
    highest = max(values)
    ticks = _nice_ticks(0.0, max(highest, 1.0), target=3)
    top = max(ticks[-1], highest or 1.0)

    drawing = Drawing(width, height)
    axis = _axis_frame(drawing, width=width, height=height, left_pad=40.0)
    _y_labels(drawing, axis, ticks, minimum=0.0, maximum=top)

    count = len(entries)
    slot = axis.width / count
    bar_width = min(slot * 0.62, 22.0)
    if bar_width < 1.5:
        bar_width = max(slot * 0.9, 1.0)

    for index, value in enumerate(values):
        if value <= 0:
            continue
        bar_height = (value / top) * axis.height
        bar_height = min(bar_height, axis.height)
        x = axis.left + slot * index + (slot - bar_width) / 2
        drawing.add(
            Rect(
                x,
                axis.bottom,
                bar_width,
                max(bar_height, 0.8),
                fillColor=bar_color,
                strokeColor=None,
            )
        )

    peak_index = values.index(highest) if highest > 0 else None
    if peak_index is not None:
        peak_x = axis.left + slot * peak_index + slot / 2
        peak_y = axis.bottom + (highest / top) * axis.height
        drawing.add(
            String(
                peak_x,
                min(peak_y + 4, axis.top - 2),
                _number(highest),
                fontName=FONTS.bold,
                fontSize=6.6,
                fillColor=NAVY,
                textAnchor="middle",
            )
        )

    labels = [_short_day(day) for day, _ in entries]
    _x_labels(drawing, axis, labels, max_labels=max_labels)
    drawing.add(
        Line(
            axis.left,
            axis.bottom,
            axis.left,
            axis.top,
            strokeColor=RULE,
            strokeWidth=0.9,
        )
    )
    return drawing


def legend_row(
    label: str,
    *,
    width: float,
    color=PRIMARY,
) -> Group:
    """Return a small colour-key row used above a chart."""

    group = Group()
    group.add(Rect(0, 1.5, 7, 7, rx=1.5, ry=1.5, fillColor=color, strokeColor=None))
    group.add(
        String(
            11,
            2.6,
            label,
            fontName=FONTS.regular,
            fontSize=7.2,
            fillColor=MUTED,
        )
    )
    return group


__all__ = [
    "consumption_chart",
    "legend_row",
    "stock_balance_chart",
]
