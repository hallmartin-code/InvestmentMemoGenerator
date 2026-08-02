"""Page geometry, font registration, and paragraph styles for the memo PDF.

Colours and typefaces come from brand.py; this module handles geometry and the
ReportLab style objects built on top of them.
"""

from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import brand

# --- Page geometry -----------------------------------------------------------

PAGE_SIZE = letter                      # 8.5 x 11 in
MARGIN = 72                             # 1 inch, all sides
USABLE_WIDTH = PAGE_SIZE[0] - 2 * MARGIN    # 6.5 in
USABLE_HEIGHT = PAGE_SIZE[1] - 2 * MARGIN   # 9 in

# Footer geometry
FOOTER_BASELINE = MARGIN / 2            # 36pt from the bottom edge
FOOTER_RULE_OFFSET = 14                 # rule sits 14pt above the footer baseline
FOOTER_RULE_WIDTH = 0.5

FOOTER_LEFT_TEXT = brand.FOOTER_LEFT_TEXT

# Spacing between story elements
GAP_AFTER_HEADER = 4
GAP_AFTER_SECTION = 10
GAP_AFTER_TITLE_BLOCK = 18

# --- Fonts -------------------------------------------------------------------

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

FONT_FILES = brand.FONT_FILES

FONT_INSTALL_INSTRUCTIONS = brand.FONT_INSTALL_INSTRUCTIONS


class FontsNotFoundError(Exception):
    """Raised when one or more brand fonts are missing from fonts/."""

    def __init__(self, missing):
        self.missing = missing
        super().__init__(
            "Missing font file(s): " + ", ".join(missing) + "\n\n"
            + f"Looked in: {FONTS_DIR}\n\n"
            + FONT_INSTALL_INSTRUCTIONS
        )


def register_fonts():
    """Register the brand typefaces with ReportLab.

    Raises FontsNotFoundError if any weight is missing.
    """
    missing = [
        filename
        for filename in FONT_FILES.values()
        if not (FONTS_DIR / filename).is_file()
    ]
    if missing:
        raise FontsNotFoundError(missing)

    for name, filename in FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, str(FONTS_DIR / filename)))

    # Body family: no italic or bold weight is used in the memo, so every slot
    # maps to the roman to keep ReportLab from synthesising one.
    pdfmetrics.registerFontFamily(
        "Inter",
        normal=brand.FONT_BODY,
        bold=brand.FONT_BODY,
        italic=brand.FONT_BODY,
        boldItalic=brand.FONT_BODY,
    )


# --- Styles ------------------------------------------------------------------

def build_styles():
    """Return the named paragraph styles. Call register_fonts() first."""
    return {
        "TITLE": ParagraphStyle(
            "TITLE",
            fontName=brand.FONT_HEADING,
            fontSize=15,
            leading=20,
            alignment=TA_LEFT,
            textColor=brand.HEADING_COLOR,
        ),
        "TAGLINE": ParagraphStyle(
            "TAGLINE",
            fontName=brand.FONT_BODY,
            fontSize=9.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=brand.MUTED_COLOR,
        ),
        "SECTION_HEADER": ParagraphStyle(
            "SECTION_HEADER",
            fontName=brand.FONT_SUBHEADING,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            textColor=brand.HEADING_COLOR,
        ),
        "BODY": ParagraphStyle(
            "BODY",
            fontName=brand.FONT_BODY,
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=brand.TEXT_COLOR,
            spaceAfter=4,
        ),
        "FOOTER": ParagraphStyle(
            "FOOTER",
            fontName=brand.FONT_MONO,
            fontSize=7.5,
            leading=10,
            textColor=brand.FOOTER_COLOR,
        ),
    }


FOOTER_FONT_NAME = brand.FONT_MONO
FOOTER_FONT_SIZE = 7.5
