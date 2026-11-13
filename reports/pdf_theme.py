"""Shared ReportLab theme: font registration, palette and paragraph styles.

The PDF report embeds a TrueType font so Turkish characters (``ç ğ ı İ ö ş ü``)
render correctly. ReportLab's built-in Type 1 fonts only cover Latin-1, which
would silently drop or mangle those glyphs.

Font resolution order:

1. The Bitstream Vera files bundled with ReportLab (portable, no OS lookup).
2. Common Windows system fonts (Segoe UI, Arial) as a fallback.
3. Helvetica, only if no TrueType font can be registered.

Registration is idempotent, so importing this module more than once is safe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont

logger = logging.getLogger(__name__)

# Design System 1.0 palette, mirrored from the Streamlit screens.
NAVY = colors.HexColor("#14243A")
NAVY_SOFT = colors.HexColor("#1E3350")
PRIMARY = colors.HexColor("#2563EB")
PRIMARY_SOFT = colors.HexColor("#EFF5FF")
PRIMARY_LIGHT = colors.HexColor("#BFD3F6")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
SUBTLE = colors.HexColor("#94A3B8")
RULE = colors.HexColor("#DCE3EC")
GRID = colors.HexColor("#E4E9F0")
ZEBRA = colors.HexColor("#F7F9FC")
PANEL = colors.HexColor("#F2F5FA")
NOTE_FILL = colors.HexColor("#FFF8EA")
NOTE_TEXT = colors.HexColor("#7A5314")
SUCCESS = colors.HexColor("#16A36A")
WARNING = colors.HexColor("#D97706")
CRITICAL = colors.HexColor("#DC4444")
WHITE = colors.white

PAGE_WIDTH, PAGE_HEIGHT = 595.2755905511812, 841.8897637795277
MARGIN = 46.0
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN


@dataclass(frozen=True)
class FontSet:
    """The four faces used by the report."""

    regular: str
    bold: str
    italic: str
    bold_italic: str


_FALLBACK = FontSet(
    regular="Helvetica",
    bold="Helvetica-Bold",
    italic="Helvetica-Oblique",
    bold_italic="Helvetica-BoldOblique",
)

_FAMILY = "IIBody"

_CANDIDATES: tuple[tuple[str, tuple[str, str, str, str]], ...] = (
    ("bundled", ("Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf")),
    ("windows", ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf")),
    ("windows", ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")),
)


def _font_directories() -> tuple[Path, ...]:
    return (
        Path(reportlab.__file__).parent / "fonts",
        Path("C:/Windows/Fonts"),
    )


def _register() -> FontSet:
    for group, names in _CANDIDATES:
        for directory in _font_directories():
            if group == "bundled" and directory.name != "fonts":
                continue
            paths = tuple(directory / name for name in names)
            if not all(path.exists() for path in paths):
                continue
            try:
                suffixes = ("", "-Bold", "-Italic", "-BoldItalic")
                for suffix, path in zip(suffixes, paths, strict=True):
                    name = f"{_FAMILY}{suffix}"
                    if name not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont(name, str(path)))
                family = FontSet(
                    regular=_FAMILY,
                    bold=f"{_FAMILY}-Bold",
                    italic=f"{_FAMILY}-Italic",
                    bold_italic=f"{_FAMILY}-BoldItalic",
                )
                pdfmetrics.registerFontFamily(
                    _FAMILY,
                    normal=family.regular,
                    bold=family.bold,
                    italic=family.italic,
                    boldItalic=family.bold_italic,
                )
                return family
            except (TTFError, OSError, ValueError) as error:  # defensive fallback
                logger.warning(
                    "Could not register report font %s: %s", paths[0], error
                )
    logger.warning("Falling back to Helvetica; Turkish glyphs may not render.")
    return _FALLBACK


FONTS = _register()


def _style(
    name: str,
    *,
    font: str,
    size: float,
    leading: float,
    color: colors.Color = TEXT,
    **kwargs,
) -> ParagraphStyle:
    return ParagraphStyle(
        name,
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        **kwargs,
    )


HERO_KICKER = _style(
    "IIHeroKicker", font=FONTS.bold, size=8.5, leading=11, color=PRIMARY_LIGHT
)
HERO_TITLE = _style(
    "IIHeroTitle", font=FONTS.bold, size=21, leading=25, color=WHITE
)
HERO_TEXT = _style(
    "IIHeroText", font=FONTS.regular, size=9.5, leading=14, color=PRIMARY_LIGHT
)

META_LABEL = _style(
    "IIMetaLabel", font=FONTS.bold, size=7.5, leading=10, color=SUBTLE
)
META_VALUE = _style(
    "IIMetaValue", font=FONTS.bold, size=10.5, leading=14, color=NAVY
)

EYEBROW = _style(
    "IIEyebrow", font=FONTS.bold, size=7.5, leading=10, color=PRIMARY
)
SECTION_TITLE = _style(
    "IISectionTitle",
    font=FONTS.bold,
    size=13.5,
    leading=17,
    color=NAVY,
    spaceAfter=1,
)
SECTION_SUB = _style(
    "IISectionSub", font=FONTS.regular, size=8.8, leading=12.5, color=MUTED
)

BODY = _style("IIBodyText", font=FONTS.regular, size=9.2, leading=13.5)
BODY_SMALL = _style("IIBodySmall", font=FONTS.regular, size=8.4, leading=12)
MUTED_SMALL = _style(
    "IIMutedSmall", font=FONTS.regular, size=8.2, leading=11.5, color=MUTED
)
NOTE = _style("IINote", font=FONTS.regular, size=8.4, leading=12.5, color=NOTE_TEXT)

TABLE_HEAD = _style(
    "IITableHead", font=FONTS.bold, size=7.8, leading=10, color=WHITE
)
TABLE_CELL = _style("IITableCell", font=FONTS.regular, size=8.6, leading=11.5)
TABLE_CELL_BOLD = _style(
    "IITableCellBold", font=FONTS.bold, size=8.6, leading=11.5, color=NAVY
)
TABLE_NUM = _style(
    "IITableNum",
    font=FONTS.regular,
    size=8.6,
    leading=11.5,
    alignment=2,
)
TABLE_NUM_BOLD = _style(
    "IITableNumBold",
    font=FONTS.bold,
    size=8.6,
    leading=11.5,
    alignment=2,
    color=NAVY,
)
TABLE_UNIT = _style(
    "IITableUnit", font=FONTS.regular, size=8.2, leading=11, color=MUTED
)

CARD_LABEL = _style(
    "IICardLabel", font=FONTS.bold, size=7.2, leading=9.5, color=MUTED
)
CARD_VALUE = _style(
    "IICardValue", font=FONTS.bold, size=15, leading=19, color=NAVY
)
CARD_META = _style(
    "IICardMeta", font=FONTS.regular, size=7.2, leading=9.5, color=SUBTLE
)

LIST_ITEM = _style(
    "IIListItem",
    font=FONTS.regular,
    size=8.6,
    leading=12.5,
    leftIndent=11,
    bulletIndent=1,
    spaceAfter=2.5,
    # The bullet must use the embedded font too, otherwise ReportLab falls back
    # to Helvetica for the marker alone.
    bulletFontName=FONTS.regular,
    bulletFontSize=8.6,
)
