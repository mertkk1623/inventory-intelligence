"""PDF report generation with ReportLab.

The document is assembled from the shared :class:`reports.report_data.ReportContext`,
so every figure matches the Excel workbook, the dashboard and the engine. The
module contains no inventory, consumption or replenishment arithmetic.

Layout: A4 portrait, white background, a navy masthead on the first page, navy
section headings with primary-blue accents, zebra tables, native ReportLab
charts and a numbered footer.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from reports import formatting as fmt
from reports.pdf_charts import consumption_chart, stock_balance_chart
from reports.pdf_theme import (
    BODY_SMALL,
    CARD_LABEL,
    CARD_META,
    CARD_VALUE,
    CONTENT_WIDTH,
    CRITICAL,
    EYEBROW,
    FONTS,
    LIST_ITEM,
    MARGIN,
    MUTED,
    MUTED_SMALL,
    NAVY,
    NOTE,
    NOTE_FILL,
    NOTE_TEXT,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    PANEL,
    PRIMARY,
    PRIMARY_LIGHT,
    RULE,
    SECTION_SUB,
    SECTION_TITLE,
    SUBTLE,
    SUCCESS,
    TABLE_CELL,
    TABLE_CELL_BOLD,
    TABLE_HEAD,
    TABLE_NUM,
    TABLE_NUM_BOLD,
    WARNING,
    WHITE,
    ZEBRA,
)
from reports.report_data import ReportContext

HERO_HEIGHT = 132.0
TOP_MARGIN = 58.0
BOTTOM_MARGIN = 56.0

_RIGHT = ParagraphStyle(
    "IIRight",
    fontName=FONTS.regular,
    fontSize=8.4,
    leading=12,
    textColor=MUTED,
    alignment=TA_RIGHT,
)

_CAPTION = ParagraphStyle(
    "IICaption",
    fontName=FONTS.regular,
    fontSize=8.2,
    leading=11.5,
    textColor=MUTED,
    spaceBefore=5,
)

_STATUS_BIG = ParagraphStyle(
    "IIStatusBig", fontName=FONTS.bold, fontSize=13, leading=17, textColor=NAVY
)

CARD_VALUE_COMPACT = ParagraphStyle(
    "IICardValueCompact", fontName=FONTS.bold, fontSize=10.5, leading=14,
    textColor=NAVY,
)

_HERO_META_LABEL = ParagraphStyle(
    "IIHeroLabel", fontName=FONTS.bold, fontSize=6.6, leading=9, textColor=PRIMARY_LIGHT
)

_KIND = {
    "core": PRIMARY,
    "good": SUCCESS,
    "warn": WARNING,
    "bad": CRITICAL,
    "muted": MUTED,
}


def build_pdf_report(context: ReportContext) -> bytes:
    """Build the complete PDF report in memory and return its bytes."""

    buffer = BytesIO()
    document = _ReportDocument(buffer, context)
    document.build(_story(context), canvasmaker=_make_canvas(document))
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Document template
# ---------------------------------------------------------------------------


class _ReportDocument(BaseDocTemplate):
    """A4 document with a masthead, running header and numbered footer."""

    def __init__(self, buffer: BytesIO, context: ReportContext) -> None:
        self.context = context
        super().__init__(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
            title=(
                f"Inventory Intelligence Report · "
                f"{context.product.product_code} · {context.report_date.isoformat()}"
            ),
            author="Inventory Intelligence",
            subject=(
                f"Inventory report for {context.product.product_code} as of "
                f"{context.report_date.isoformat()}"
            ),
            creator="Inventory Intelligence",
            keywords="inventory, stock, consumption, replenishment",
        )

        first_height = PAGE_HEIGHT - HERO_HEIGHT - BOTTOM_MARGIN - 16.0
        first_frame = Frame(
            MARGIN,
            BOTTOM_MARGIN,
            CONTENT_WIDTH,
            first_height,
            id="first",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        later_frame = Frame(
            MARGIN,
            BOTTOM_MARGIN,
            CONTENT_WIDTH,
            PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
            id="later",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="first", frames=[first_frame], onPage=self._draw_masthead
                ),
                PageTemplate(
                    id="later", frames=[later_frame], onPage=self._draw_running_head
                ),
            ]
        )

    # -- page furniture ---------------------------------------------------

    def _draw_masthead(self, canvas, document) -> None:
        context = self.context
        top = PAGE_HEIGHT
        left = MARGIN
        right = PAGE_WIDTH - MARGIN

        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, top - HERO_HEIGHT, PAGE_WIDTH, HERO_HEIGHT, stroke=0, fill=1)
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, top - HERO_HEIGHT - 3, PAGE_WIDTH, 3, stroke=0, fill=1)

        # Kicker line.
        kicker = "INVENTORY INTELLIGENCE"
        canvas.setFillColor(PRIMARY_LIGHT)
        canvas.setFont(FONTS.bold, 7.6)
        canvas.drawString(left, top - 30, kicker)
        canvas.setFont(FONTS.regular, 7.6)
        canvas.drawString(
            left + canvas.stringWidth(kicker, FONTS.bold, 7.6) + 7,
            top - 30,
            "· STOCK & MATERIAL PLANNING",
        )

        # Title.
        canvas.setFillColor(WHITE)
        canvas.setFont(FONTS.bold, 20)
        canvas.drawString(left, top - 58, "Inventory Report")

        # Product line: the full name always fits here, so it is never cut.
        canvas.setFillColor(PRIMARY_LIGHT)
        canvas.setFont(FONTS.regular, 9.2)
        canvas.drawString(
            left,
            top - 78,
            f"{context.product.product_code} · {context.product.product_name} · "
            f"{context.unit}",
        )

        # Report-type pill, right-aligned with the title.
        badge = context.report_type_label
        badge_width = canvas.stringWidth(badge, FONTS.bold, 7.2) + 18
        canvas.setFillColor(PRIMARY)
        canvas.roundRect(right - badge_width, top - 66, badge_width, 16, 8, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONTS.bold, 7.2)
        canvas.drawString(right - badge_width + 9, top - 61, badge)

        # Metadata strip.
        canvas.setStrokeColor(PRIMARY_LIGHT)
        canvas.setLineWidth(0.5)
        canvas.line(left, top - 94, right, top - 94)

        meta = (
            ("REPORT DATE", fmt.day(context.report_date)),
            ("GENERATED", fmt.timestamp(context.generated_at)),
            ("MOVEMENTS", f"{context.dataset.movement_count} in workbook"),
            ("SOURCE", context.source_label),
        )
        width = CONTENT_WIDTH / len(meta)
        for index, (label, value) in enumerate(meta):
            x = left + width * index
            canvas.setFillColor(PRIMARY_LIGHT)
            canvas.setFont(FONTS.bold, 6.6)
            canvas.drawString(x, top - 106, label)
            canvas.setFillColor(WHITE)
            canvas.setFont(FONTS.bold, 8.6)
            canvas.drawString(x, top - 119, value)
        canvas.restoreState()

    def _draw_running_head(self, canvas, document) -> None:
        context = self.context
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.setFont(FONTS.bold, 8)
        canvas.drawString(MARGIN, PAGE_HEIGHT - 34, "INVENTORY INTELLIGENCE")
        canvas.setFillColor(MUTED)
        canvas.setFont(FONTS.regular, 7.6)
        canvas.drawRightString(
            PAGE_WIDTH - MARGIN,
            PAGE_HEIGHT - 34,
            f"{context.product.product_code} · Report date "
            f"{fmt.day(context.report_date)}",
        )
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, PAGE_HEIGHT - 40, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 40)
        canvas.restoreState()

    def _draw_footer(self, canvas, page_number: int, total: int) -> None:
        context = self.context
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, 42, PAGE_WIDTH - MARGIN, 42)

        canvas.setFillColor(SUBTLE)
        canvas.setFont(FONTS.regular, 7.2)
        canvas.drawString(
            MARGIN,
            31,
            "Generated by Inventory Intelligence · values come from the "
            f"validated workbook '{context.dataset.filename}'",
        )
        canvas.drawRightString(
            PAGE_WIDTH - MARGIN,
            31,
            f"Page {page_number} of {total}",
        )
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, 0, PAGE_WIDTH, 3, stroke=0, fill=1)
        canvas.restoreState()


def _make_canvas(document: _ReportDocument):
    """Return a canvas class that can render ``Page X of Y`` in the footer."""

    from reportlab.pdfgen.canvas import Canvas

    class NumberedCanvas(Canvas):
        """Draws the footer once the total page count is known."""

        def __init__(self, *args, **kwargs):
            Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states: list[dict] = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                document._draw_footer(self, self._pageNumber, total)
                Canvas.showPage(self)
            Canvas.save(self)

    return NumberedCanvas


# ---------------------------------------------------------------------------
# Story
# ---------------------------------------------------------------------------

_OVERVIEW = (
    ("02", "Stock Analysis", "Opening position, movement totals and the daily closing balance."),
    ("03", "Consumption Analysis", "Daily and weekly consumption for the reporting window."),
    ("04", "Replenishment Planning", "Planning thresholds, reorder status and suggested order."),
    ("05", "Open Purchase Orders", "Orders awaiting delivery and their overdue status."),
    ("06", "Methodology & Notes", "Formulas, report facts and reporting limitations."),
)


def _story(context: ReportContext) -> list[Flowable]:
    story: list[Flowable] = [
        KeepTogether(
            [
                _section_heading(
                    "01",
                    "Executive Summary",
                    "The headline position at the selected report date.",
                ),
                Spacer(1, 9),
                _kpi_cards(context),
                Spacer(1, 12),
                _status_panels(context),
            ]
        ),
        Spacer(1, 16),
        _scope_panel(context),
        Spacer(1, 16),
        _contents_panel(),
        NextPageTemplate("later"),
        PageBreak(),
        KeepTogether(
            [
                _section_heading(
                    "02",
                    "Stock Analysis",
                    "Opening position, movement totals and the daily closing balance.",
                ),
                Spacer(1, 9),
                _stock_table(context),
            ]
        ),
        Spacer(1, 12),
    ]
    story.extend(
        _chart_block(
            "Stock balance trend",
            stock_balance_chart(
                context.balance_points,
                width=CONTENT_WIDTH,
                height=168.0,
            ),
            "Closing stock balance for every calendar day from the opening date "
            f"through {fmt.day(context.report_date)}.",
        )
    )
    story.extend(
        [
            CondPageBreak(240),
            _section_heading(
                "03",
                "Consumption Analysis",
                _consumption_caption(context),
            ),
            Spacer(1, 9),
            _consumption_summary_table(context),
            Spacer(1, 12),
        ]
    )
    story.extend(
        _chart_block(
            "Daily consumption",
            consumption_chart(
                tuple((entry.day, entry.quantity) for entry in context.daily),
                width=CONTENT_WIDTH,
                height=132.0,
                empty_message="No consumption window available.",
            ),
            "Zero-filled daily OUT consumption across the reporting window.",
        )
    )
    story.extend(
        _chart_block(
            "Weekly consumption",
            consumption_chart(
                tuple((entry.week_start, entry.quantity) for entry in context.weekly),
                width=CONTENT_WIDTH,
                height=126.0,
                max_labels=8,
                empty_message="No weekly consumption available.",
            ),
            "Weekly OUT consumption, grouped by the Monday of each week.",
        )
    )

    story.append(CondPageBreak(330))
    story.append(
        _section_heading(
            "04",
            "Replenishment Planning",
            "Planning thresholds derived from the consumption window ending "
            "on the report date.",
        )
    )
    story.append(Spacer(1, 9))
    story.append(_replenishment_table(context))
    note = _replenishment_note(context)
    if note is not None:
        story.extend([Spacer(1, 10), note])

    story.append(Spacer(1, 20))
    story.extend(_orders_block(context))

    story.append(Spacer(1, 18))
    story.append(CondPageBreak(400))
    story.append(
        _section_heading(
            "06",
            "Methodology & Notes",
            "How every figure in this report is produced.",
        )
    )
    story.append(Spacer(1, 9))
    story.append(_notes_table(context))
    return story


def _section_heading(number: str, title: str, subtitle: str) -> Table:
    """Return a heading block: numbered eyebrow, title, subtitle and rule."""

    block = Table(
        [
            [Paragraph(f"{number} · REPORT SECTION", EYEBROW)],
            [Paragraph(title, SECTION_TITLE)],
            [Paragraph(subtitle, SECTION_SUB)],
        ],
        colWidths=[CONTENT_WIDTH],
    )
    block.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 3),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 2), (0, 2), 6),
                ("LINEBELOW", (0, 2), (0, 2), 1.1, NAVY),
            ]
        )
    )
    return block


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------


def _kpi_cards(context: ReportContext) -> Table:
    calculation = context.calculation
    unit = context.unit
    supported = calculation.replenishment_supported

    suggestions = (
        fmt.quantity(calculation.suggested_order_quantity, unit)
        if supported
        else "Not generated"
    )
    if not supported:
        suggestion_meta = "Historical report"
    elif calculation.reorder_required:
        suggestion_meta = "Reorder required"
    else:
        suggestion_meta = "No action required"

    cards = [
        (
            "CURRENT STOCK",
            fmt.quantity(calculation.current_stock, unit),
            f"Opening {fmt.quantity(context.product.opening_stock, unit)}",
        ),
        (
            "AVG DAILY CONSUMPTION",
            fmt.decimal(calculation.average_daily_consumption, unit, places=2),
            f"{calculation.consumption_coverage_days} calendar days",
        ),
        (
            "DAYS OF SUPPLY",
            fmt.days(calculation.days_of_supply),
            (
                "Current stock / average consumption"
                if calculation.days_of_supply is not None
                else "Not reported when consumption is zero"
            ),
        ),
        ("SUGGESTED ORDER", suggestions, suggestion_meta),
    ]

    cells = []
    for label, value, meta in cards:
        # Long conditional values ("Not generated") would wrap and collide with
        # the meta line, so shrink them instead of letting the card grow.
        value_style = CARD_VALUE if len(value) <= 11 else CARD_VALUE_COMPACT
        cells.append(
            [
                Paragraph(label, CARD_LABEL),
                Paragraph(value, value_style),
                Paragraph(meta, CARD_META),
            ]
        )

    card_width = (CONTENT_WIDTH - 8.0 * 3) / 4
    table = Table([cells], colWidths=[card_width] * 4, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LINEABOVE", (0, 0), (-1, 0), 2, PRIMARY),
            ]
        )
    )
    return table


def _status_panels(context: ReportContext) -> Table:
    """Return two side-by-side status panels, each built as its own table.

    Nested tables avoid the merged-cell pitfall where a spanning cell silently
    discards the value next to its label.
    """

    calculation = context.calculation
    unit = context.unit
    supported = calculation.replenishment_supported

    if not supported:
        status = "Historical report"
        tone = "muted"
        detail = (
            "Replenishment planning is supported only for the current report "
            "date, so no order suggestion is generated here."
        )
    elif calculation.reorder_required:
        status = "Reorder required"
        tone = "warn"
        detail = (
            "Inventory Position is at or below the Reorder Point. The suggested "
            "order quantity restores the Target Stock."
        )
    else:
        status = "No action required"
        tone = "good"
        detail = (
            "Inventory Position is above the Reorder Point, so no new purchase "
            "order is suggested for this report date."
        )

    left_width = CONTENT_WIDTH * 0.52
    right_width = CONTENT_WIDTH - left_width

    left = Table(
        [
            [Paragraph("PLANNING STATUS", CARD_LABEL)],
            [
                Paragraph(
                    f'<font color="#{_hex(_KIND[tone])}">{status}</font>',
                    _STATUS_BIG,
                )
            ],
            [Paragraph(detail, MUTED_SMALL)],
        ],
        colWidths=[left_width - 20],
    )
    left.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ("TOPPADDING", (0, 2), (0, 2), 2),
                ("BOTTOMPADDING", (0, 2), (0, 2), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    # The engine already decides whether open orders belong in the position, so
    # the report never recomputes it.
    position = fmt.quantity(calculation.inventory_position, unit)
    right = Table(
        [
            [Paragraph("INVENTORY POSITION", CARD_LABEL)],
            [Paragraph(position, _STATUS_BIG)],
            [
                Paragraph(
                    f"Reorder point {fmt.decimal(calculation.reorder_point, unit)} "
                    f"· target stock {fmt.decimal(calculation.target_stock, unit)}",
                    MUTED_SMALL,
                )
            ],
        ],
        colWidths=[right_width - 20],
    )
    right.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ("TOPPADDING", (0, 2), (0, 2), 2),
                ("BOTTOMPADDING", (0, 2), (0, 2), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    outer = Table([[left, right]], colWidths=[left_width, right_width])
    outer.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, RULE),
                ("LINEBEFORE", (1, 0), (1, -1), 0.7, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 11),
                ("RIGHTPADDING", (0, 0), (0, 0), 12),
                ("LEFTPADDING", (1, 0), (1, 0), 12),
                ("RIGHTPADDING", (1, 0), (1, 0), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return outer


def _scope_panel(context: ReportContext) -> Table:
    """Return a compact report-scope table that fills the summary page."""

    product = context.product
    calculation = context.calculation
    movement_rows = len(context.movement_rows())
    rows = [
        ("Product code", product.product_code),
        ("Product name", product.product_name),
        ("Unit of measure", product.unit),
        ("Opening stock date", fmt.day(product.opening_stock_date)),
        (
            "Movements in range",
            f"{movement_rows} of {context.dataset.movement_count}",
        ),
        ("Open purchase orders", f"{len(context.open_orders)}"),
        (
            "Replenishment support",
            "Enabled" if calculation.replenishment_supported else "Not available for historical dates",
        ),
    ]
    body = [
        [
            Paragraph(label, TABLE_CELL),
            Paragraph(value, TABLE_CELL_BOLD),
        ]
        for label, value in rows
    ]
    table = _table(
        ("Report Scope", "Value"),
        body,
        (CONTENT_WIDTH * 0.30, CONTENT_WIDTH * 0.70),
    )
    return table


def _contents_panel() -> Table:
    """Return the report contents list."""

    rows = [
        [
            Paragraph(number, ParagraphStyle(
                "IIContentsNum",
                fontName=FONTS.bold,
                fontSize=8,
                leading=12,
                textColor=PRIMARY,
            )),
            Paragraph(title, TABLE_CELL_BOLD),
            Paragraph(description, MUTED_SMALL),
        ]
        for number, title, description in _OVERVIEW
    ]
    table = Table(
        [[Paragraph("IN THIS REPORT", EYEBROW)], *rows],
        colWidths=[CONTENT_WIDTH * 0.07, CONTENT_WIDTH * 0.29, CONTENT_WIDTH * 0.64],
    )
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LINEBELOW", (0, 1), (-1, -2), 0.5, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _hex(color) -> str:
    return color.hexval()[2:].upper()


# ---------------------------------------------------------------------------
# Stock analysis
# ---------------------------------------------------------------------------


def _stock_table(context: ReportContext) -> Table:
    calculation = context.calculation
    product = context.product
    unit = context.unit

    rows = [
        (
            "Opening Stock",
            fmt.quantity(product.opening_stock, unit),
            fmt.day(product.opening_stock_date),
        ),
        (
            "Current Stock",
            fmt.quantity(calculation.current_stock, unit),
            f"as of {fmt.day(context.report_date)}",
        ),
        ("Total IN", fmt.quantity(calculation.total_in, unit), "incoming movements in range"),
        ("Total OUT", fmt.quantity(calculation.total_out, unit), "outgoing movements in range"),
        ("Safety Stock", fmt.quantity(calculation.safety_stock, unit), "minimum planning buffer"),
    ]
    return _table(
        ("Measure", "Value", "Basis"),
        [
            (
                Paragraph(label, TABLE_CELL),
                Paragraph(value, TABLE_NUM_BOLD),
                Paragraph(note, MUTED_SMALL),
            )
            for label, value, note in rows
        ],
        (CONTENT_WIDTH * 0.30, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.48),
    )


def _chart_block(title: str, chart, caption: str) -> list[Flowable]:
    """Return a keep-together chart block: title, chart, then caption."""

    return [
        KeepTogether(
            [
                Paragraph(title, TABLE_CELL_BOLD),
                Spacer(1, 5),
                chart,
                Paragraph(caption, _CAPTION),
                Spacer(1, 12),
            ]
        )
    ]


# ---------------------------------------------------------------------------
# Consumption
# ---------------------------------------------------------------------------


def _consumption_caption(context: ReportContext) -> str:
    if not context.daily:
        return "No consumption window is available for this report date."
    return (
        "OUT consumption from "
        f"{fmt.day(context.consumption_start)} to {fmt.day(context.consumption_end)} "
        f"({len(context.daily)} calendar days)."
    )


def _consumption_summary_table(context: ReportContext) -> Table:
    summary = context.summary
    calculation = context.calculation
    unit = context.unit

    rows = [
        (
            "Average daily consumption",
            fmt.decimal(calculation.average_daily_consumption, unit, places=2),
            f"{calculation.consumption_coverage_days} covered days",
        ),
        (
            "Total consumption",
            fmt.quantity(summary.total, unit),
            f"{len(context.daily)} days in window",
        ),
        (
            "Highest consumption day",
            fmt.quantity(summary.highest_quantity, unit),
            fmt.day(summary.highest_day) if summary.highest_day else "No consumption",
        ),
        (
            "Lowest consumption day",
            fmt.quantity(summary.lowest_quantity, unit),
            fmt.day(summary.lowest_day) if summary.lowest_day else "No window",
        ),
        (
            "Weekly average",
            fmt.decimal(_weekly_average(context), unit, places=2),
            f"{len(context.weekly)} calendar weeks",
        ),
    ]
    return _table(
        ("Measure", "Value", "Detail"),
        [
            (
                Paragraph(label, TABLE_CELL),
                Paragraph(value, TABLE_NUM_BOLD),
                Paragraph(note, MUTED_SMALL),
            )
            for label, value, note in rows
        ],
        (CONTENT_WIDTH * 0.34, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.44),
    )


def _weekly_average(context: ReportContext) -> float:
    if not context.weekly:
        return 0.0
    total = sum(entry.quantity for entry in context.weekly)
    return total / len(context.weekly)


# ---------------------------------------------------------------------------
# Replenishment
# ---------------------------------------------------------------------------


def _replenishment_table(context: ReportContext) -> Table:
    calculation = context.calculation
    unit = context.unit
    supported = calculation.replenishment_supported

    rows = [
        (
            "Reorder Point",
            fmt.decimal(calculation.reorder_point, unit),
            "consumption × lead time + safety stock",
        ),
        ("Safety Stock", fmt.quantity(calculation.safety_stock, unit), "minimum buffer"),
        ("Lead Time", f"{calculation.lead_time_days} days", "supplier delivery time"),
        ("Current Stock", fmt.quantity(calculation.current_stock, unit), "physical balance"),
        (
            "Open Order Quantity",
            fmt.quantity(calculation.total_open_order_quantity, unit)
            if supported
            else "Not included",
            "incoming supply" if supported else "excluded from historical reports",
        ),
        (
            "Inventory Position",
            fmt.quantity(calculation.inventory_position, unit),
            "current stock + open orders" if supported else "current stock only",
        ),
        (
            "Target Stock",
            fmt.decimal(calculation.target_stock, unit),
            "restores coverage after lead time",
        ),
        (
            "Suggested Order Quantity",
            fmt.quantity(calculation.suggested_order_quantity, unit)
            if supported
            else "Not generated",
            "new purchase order quantity",
        ),
        (
            "Reorder Required",
            ("Yes" if calculation.reorder_required else "No")
            if supported
            else "Not supported",
            "position at or below reorder point"
            if supported
            else "not evaluated historically",
        ),
    ]
    return _table(
        ("Planning Field", "Value", "Basis"),
        [
            (
                Paragraph(label, TABLE_CELL),
                Paragraph(value, TABLE_NUM_BOLD),
                Paragraph(note, MUTED_SMALL),
            )
            for label, value, note in rows
        ],
        (CONTENT_WIDTH * 0.30, CONTENT_WIDTH * 0.24, CONTENT_WIDTH * 0.46),
    )


def _replenishment_note(context: ReportContext) -> Flowable | None:
    calculation = context.calculation
    if calculation.replenishment_note:
        return _note_box(calculation.replenishment_note, tone=WARNING)
    if calculation.negative_stock_warning:
        return _note_box(
            "Negative stock warning: the running balance fell to "
            f"{calculation.lowest_stock_balance:,} {context.unit}. The balance is "
            "reported without clamping.",
            tone=CRITICAL,
        )
    return None


# ---------------------------------------------------------------------------
# Open purchase orders
# ---------------------------------------------------------------------------


def _orders_block(context: ReportContext) -> list[Flowable]:
    supported = context.calculation.replenishment_supported
    block: list[Flowable] = [
        # Keep the section heading with at least the table header so it never
        # ends up alone at the bottom of a page.
        CondPageBreak(150),
        _section_heading(
            "05",
            "Open Purchase Orders",
            "Orders awaiting delivery. Overdue means the expected delivery date "
            "is before the report date.",
        ),
        Spacer(1, 9),
    ]

    if not context.open_orders:
        block.append(
            _note_box("This dataset contains no open purchase orders.", tone=MUTED)
        )
        return block

    rows = []
    for entry in context.open_orders:
        overdue = entry.is_overdue
        status = Paragraph(
            f'<font color="#{_hex(CRITICAL if overdue else SUCCESS)}">'
            f'{"Overdue" if overdue else "On schedule"}</font>',
            ParagraphStyle(
                "IIOrderStatus", fontName=FONTS.bold, fontSize=8.6, leading=11.5,
                alignment=2,
            ),
        )
        rows.append(
            (
                Paragraph(entry.order.order_no, TABLE_CELL_BOLD),
                Paragraph(
                    fmt.quantity(entry.order.order_quantity, context.unit), TABLE_NUM
                ),
                Paragraph(fmt.day(entry.order.expected_delivery_date), TABLE_CELL),
                status,
            )
        )

    block.append(
        _table(
            (
                "Order Number",
                "Order Quantity",
                "Expected Delivery Date",
                "Overdue Status",
            ),
            rows,
            (
                CONTENT_WIDTH * 0.28,
                CONTENT_WIDTH * 0.22,
                CONTENT_WIDTH * 0.28,
                CONTENT_WIDTH * 0.22,
            ),
        )
    )

    total = sum(int(entry.order.order_quantity) for entry in context.open_orders)
    overdue_count = sum(1 for entry in context.open_orders if entry.is_overdue)
    block.append(Spacer(1, 6))
    block.append(
        Paragraph(
            f"{len(context.open_orders)} open order"
            f"{'s' if len(context.open_orders) != 1 else ''} · "
            f"total quantity {fmt.quantity(total, context.unit)} · "
            f"{overdue_count} overdue",
            MUTED_SMALL,
        )
    )

    if not supported:
        block.append(Spacer(1, 8))
        block.append(
            _note_box(
                "Historical report: the orders above are shown for reference only "
                "and are excluded from Inventory Position.",
                tone=WARNING,
            )
        )
    return block


# ---------------------------------------------------------------------------
# Methodology
# ---------------------------------------------------------------------------


def _notes_table(context: ReportContext) -> Table:
    supported = context.calculation.replenishment_supported
    window = (
        f"{fmt.day(context.consumption_start)} to {fmt.day(context.consumption_end)}"
        if context.daily
        else "not available"
    )

    facts = [
        ("Report date", fmt.day(context.report_date)),
        ("Consumption window", window),
        (
            "Open PO rule",
            "Open orders are included in Inventory Position as incoming supply."
            if supported
            else "Open orders are excluded from Inventory Position in historical reports.",
        ),
        ("Report source", f"{context.source_label} · {context.dataset.filename}"),
        ("Generation time", fmt.timestamp(context.generated_at)),
    ]

    facts_table = _table(
        ("Report Fact", "Value"),
        [
            (Paragraph(label, TABLE_CELL), Paragraph(value, TABLE_CELL))
            for label, value in facts
        ],
        (CONTENT_WIDTH * 0.28, CONTENT_WIDTH * 0.72),
    )

    notes = [Paragraph(note, LIST_ITEM, bulletText="•") for note in context.notes]
    notes_block = Table([[notes]], colWidths=[CONTENT_WIDTH])
    notes_block.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    disclaimer = Paragraph(
        "<b>Scope.</b> This report describes one product for one report date. It "
        "contains no forecasts, no AI-generated recommendations and no automatic "
        "purchase orders. Stock, consumption and replenishment values are "
        "produced by the Inventory Intelligence calculation engine from the "
        "validated workbook; the report layer only formats them.",
        MUTED_SMALL,
    )

    wrapper = Table(
        [
            [facts_table],
            [Spacer(1, 10)],
            [Paragraph("CALCULATION METHODOLOGY", EYEBROW)],
            [Spacer(1, 4)],
            [notes_block],
            [Spacer(1, 10)],
            [disclaimer],
        ],
        colWidths=[CONTENT_WIDTH],
    )
    wrapper.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrapper


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


def _table(
    headers: tuple[str, ...],
    rows: list[tuple],
    widths: tuple[float, ...],
) -> Table:
    data: list[list] = [[Paragraph(header, TABLE_HEAD) for header in headers]]
    data.extend([list(row) for row in rows])

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, RULE),
        ("BOX", (0, 0), (-1, -1), 0.7, RULE),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
    ]
    for index in range(1, len(data)):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), ZEBRA))

    table = Table(data, colWidths=list(widths), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle(style))
    return table


_NOTE_STYLES = {
    "warn": (NOTE_FILL, WARNING, NOTE_TEXT),
    "bad": (NOTE_FILL, CRITICAL, CRITICAL),
    "muted": (PANEL, MUTED, MUTED),
}


def _note_box(text: str, *, tone) -> Table:
    fill, accent, text_color = _NOTE_STYLES.get(
        "muted" if tone is MUTED else ("bad" if tone is CRITICAL else "warn"),
        _NOTE_STYLES["warn"],
    )
    style = ParagraphStyle(
        "IINoteBox",
        parent=NOTE if text_color is NOTE_TEXT else BODY_SMALL,
        textColor=text_color,
    )
    table = Table([[Paragraph(text, style)]], colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("LINEBEFORE", (0, 0), (0, -1), 2.4, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table
