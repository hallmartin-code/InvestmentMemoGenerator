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

# Spacing between story elements.
#
# The reference memo is a Google Docs export: 12pt before and after each body
# paragraph and each bulleted *list*, but zero between items inside a list.
# That rhythm is preserved here, scaled down for print — at Docs' spacing a
# fifteen-section memo runs half again as long without reading any better.
# Heading spacing lives on the paragraph styles rather than in Spacer
# flowables: a Spacer between a heading and its body satisfies keepWithNext,
# which then happily strands the heading alone at the foot of a page.
GAP_AFTER_HEADER = 5
GAP_AFTER_SUBHEADER = 3
GAP_BEFORE_SECTION = 14
GAP_BEFORE_SUBSECTION = 9
GAP_AROUND_LIST = 4
GAP_AFTER_TITLE_BLOCK = 16
GAP_AFTER_META_BLOCK = 8

# Bulleted list geometry
BULLET_INDENT = 12
BULLET_OFFSET = 5

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

    # Body family: <b> resolves to Inter SemiBold, which the memo uses for the
    # inline labels on "Label: value" lines. No italic is used, so those slots
    # map to the roman to keep ReportLab from synthesising one.
    pdfmetrics.registerFontFamily(
        "Inter",
        normal=brand.FONT_BODY,
        bold=brand.FONT_BODY_BOLD,
        italic=brand.FONT_BODY,
        boldItalic=brand.FONT_BODY_BOLD,
    )


# --- Styles ------------------------------------------------------------------

def build_styles():
    """Return the named paragraph styles. Call register_fonts() first.

    The size ramp mirrors the reference memo's hierarchy (body / subheading /
    section / title at roughly 1 : 1.15 : 1.35 : 1.8) in the brand typefaces
    rather than the reference's Open Sans, so the memo still reads as a TEN
    Capital document.
    """
    return {
        "TITLE": ParagraphStyle(
            "TITLE",
            fontName=brand.FONT_HEADING,
            fontSize=17,
            leading=21,
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
        # "Label: value" lines in the header block, label set bold via <b>.
        "META": ParagraphStyle(
            "META",
            fontName=brand.FONT_BODY,
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=brand.TEXT_COLOR,
        ),
        "SECTION_HEADER": ParagraphStyle(
            "SECTION_HEADER",
            fontName=brand.FONT_HEADING,
            fontSize=12.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=brand.HEADING_COLOR,
            spaceBefore=GAP_BEFORE_SECTION,
            spaceAfter=GAP_AFTER_HEADER,
            keepWithNext=1,
        ),
        "SUBSECTION_HEADER": ParagraphStyle(
            "SUBSECTION_HEADER",
            fontName=brand.FONT_SUBHEADING,
            fontSize=10.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=brand.SUBHEADING_COLOR,
            spaceBefore=GAP_BEFORE_SUBSECTION,
            spaceAfter=GAP_AFTER_SUBHEADER,
            keepWithNext=1,
        ),
        "BODY": ParagraphStyle(
            "BODY",
            fontName=brand.FONT_BODY,
            fontSize=9.5,
            leading=13.5,
            alignment=TA_LEFT,
            textColor=brand.TEXT_COLOR,
            spaceAfter=5,
        ),
        # Zero spaceAfter: the reference sets list items solid and puts the
        # air before and after the list as a whole.
        "BULLET": ParagraphStyle(
            "BULLET",
            fontName=brand.FONT_BODY,
            fontSize=9.5,
            leading=13.5,
            alignment=TA_LEFT,
            textColor=brand.TEXT_COLOR,
            leftIndent=BULLET_INDENT,
            bulletIndent=BULLET_OFFSET,
            spaceAfter=0,
        ),
        "CLOSING": ParagraphStyle(
            "CLOSING",
            fontName=brand.FONT_SUBHEADING,
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=brand.MUTED_COLOR,
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
