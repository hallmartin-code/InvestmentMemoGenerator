"""TEN Capital Network brand system.

Palette, typefaces, and marks, transcribed from the TEN Capital Deck Analyzer
reference page. This is the single source of brand truth — colours and fonts
live here, not scattered through the renderer.

Screen-to-print adaptation: the reference is a dark UI. Reversing a full navy
page for print would be unreadable and toner-heavy, so the memo runs navy ink
on white, with the brand asserted through the masthead band, the tri-colour
rule, and the typeface pairing.
"""

from reportlab.lib.colors import HexColor

# --- Palette -----------------------------------------------------------------
# Names and values match the CSS custom properties in the reference page.

NAVY_950 = HexColor("#0B1526")
NAVY_900 = HexColor("#101E33")
NAVY_800 = HexColor("#16283F")
NAVY_700 = HexColor("#1E354F")

CORAL = HexColor("#EE5A4E")
CORAL_SOFT = HexColor("#F0776C")
AMBER = HexColor("#F3A22A")
TEAL = HexColor("#35BEBB")

INK_100 = HexColor("#F3F6FA")
INK_300 = HexColor("#C4D0E0")
INK_500 = HexColor("#7E90A8")
INK_600 = HexColor("#5C6E86")

# Print roles
TEXT_COLOR = NAVY_900          # body copy
HEADING_COLOR = NAVY_950       # company name, section headers
MUTED_COLOR = INK_600          # tagline, secondary copy
RULE_COLOR = INK_300           # hairlines
FOOTER_COLOR = INK_600
ACCENT_SEQUENCE = (CORAL, AMBER, TEAL)

# --- Typefaces ---------------------------------------------------------------
# Sora for headings, Inter for body, JetBrains Mono for metadata — the same
# pairing as the reference page.

FONT_FILES = {
    "Sora-Bold": "Sora-Bold.ttf",
    "Sora-SemiBold": "Sora-SemiBold.ttf",
    "Inter-Regular": "Inter-Regular.ttf",
    "JetBrainsMono-Medium": "JetBrainsMono-Medium.ttf",
}

FONT_HEADING = "Sora-Bold"
FONT_SUBHEADING = "Sora-SemiBold"
FONT_BODY = "Inter-Regular"
FONT_MONO = "JetBrainsMono-Medium"

FONT_INSTALL_INSTRUCTIONS = """The TEN Capital brand fonts are Sora, Inter, and JetBrains Mono.

Fetch them automatically (needs `pip install fonttools`):

    python tools/fetch_brand_fonts.py

Or download each family from Google Fonts and copy the static weights into
fonts/ with these exact names:

    Sora-Bold.ttf                https://fonts.google.com/specimen/Sora
    Sora-SemiBold.ttf            https://fonts.google.com/specimen/Sora
    Inter-Regular.ttf            https://fonts.google.com/specimen/Inter
    JetBrainsMono-Medium.ttf     https://fonts.google.com/specimen/JetBrains+Mono

Sora and Inter download as variable fonts, which ReportLab cannot read — use
the files from each archive's static/ folder, or the fetch script above."""

# --- Masthead geometry -------------------------------------------------------

BAND_HEIGHT = 54               # full-bleed navy band, first page only
ACCENT_RULE_HEIGHT = 2.5       # coral -> amber -> teal rule beneath the band
BAND_GAP_BELOW = 24            # space between the rule and the first flowable

LOGO_SIZE = 26
LOGO_INSET = 40                # left inset of the mark inside the band

WORDMARK = "TEN CAPITAL"
WORDMARK_SUB = "NETWORK"
EYEBROW = "INVESTMENT MEMO"

FOOTER_LEFT_TEXT = "TEN CAPITAL — CONFIDENTIAL"
FOOTER_CHAR_SPACE = 0.4        # mono letter-spacing, echoing the reference


def band_total_height():
    """Vertical space the masthead consumes on the first page."""
    return BAND_HEIGHT + ACCENT_RULE_HEIGHT + BAND_GAP_BELOW


# --- Text helpers ------------------------------------------------------------

def tracked_width(canvas, text, font, size, tracking):
    """Width of `text` including letter-spacing."""
    return canvas.stringWidth(text, font, size) + tracking * len(text)


def draw_tracked_string(
    canvas, x, y, text, font, size, color, tracking=0.0, align="left"
):
    """Draw letter-spaced text.

    Letter-spacing is a text-object property in ReportLab — the canvas has no
    setCharSpace — so this goes through beginText/drawText.
    """
    if align == "right":
        x -= tracked_width(canvas, text, font, size, tracking)

    text_object = canvas.beginText(x, y)
    text_object.setFont(font, size)
    text_object.setFillColor(color)
    if tracking:
        text_object.setCharSpace(tracking)
    text_object.textOut(text)
    canvas.drawText(text_object)


# --- Marks -------------------------------------------------------------------

def draw_logo(canvas, x, y, size=LOGO_SIZE):
    """Draw the tri-figure mark with its bottom-left corner at (x, y).

    Transcribed from the reference SVG (viewBox 0 0 100 100), converting its
    y-down coordinates to PDF y-up. The source applies rotate(180) to the coral
    arc, which lands it on top of the teal one; mirroring it to sit under the
    coral figure is clearly what was meant, so it is drawn un-rotated here.
    """
    scale = size / 100.0

    def point(px, py):
        return (x + px * scale, y + (100 - py) * scale)

    canvas.saveState()
    canvas.setLineWidth(11 * scale)
    canvas.setLineCap(1)  # round

    arcs = [
        (AMBER, (50, 6), (64, 6), (74, 16), (74, 16)),
        (TEAL, (76, 66), (76, 82), (63, 92), (63, 92)),
        (CORAL, (24, 66), (24, 82), (37, 92), (37, 92)),
    ]
    for color, start, control_1, control_2, end in arcs:
        canvas.setStrokeColor(color)
        path = canvas.beginPath()
        path.moveTo(*point(*start))
        path.curveTo(*point(*control_1), *point(*control_2), *point(*end))
        canvas.drawPath(path, stroke=1, fill=0)

    figures = [
        (AMBER, (50, 20)),
        (TEAL, (78, 68)),
        (CORAL, (22, 68)),
    ]
    for color, center in figures:
        canvas.setFillColor(color)
        cx, cy = point(*center)
        canvas.circle(cx, cy, 11 * scale, stroke=0, fill=1)

    canvas.restoreState()


def draw_accent_rule(canvas, x, y, width, height=ACCENT_RULE_HEIGHT):
    """Draw the coral -> amber -> teal gradient rule."""
    canvas.saveState()
    clip = canvas.beginPath()
    clip.rect(x, y, width, height)
    canvas.clipPath(clip, stroke=0, fill=0)
    canvas.linearGradient(
        x, y, x + width, y,
        list(ACCENT_SEQUENCE),
        positions=[0.0, 0.5, 1.0],
        extend=True,
    )
    canvas.restoreState()


def draw_masthead(canvas, page_width, page_height, margin):
    """Draw the first-page masthead: navy band, logo, wordmark, accent rule."""
    band_bottom = page_height - BAND_HEIGHT

    # Band, gradient navy-900 -> navy-800 as on the reference card.
    canvas.saveState()
    clip = canvas.beginPath()
    clip.rect(0, band_bottom, page_width, BAND_HEIGHT)
    canvas.clipPath(clip, stroke=0, fill=0)
    canvas.linearGradient(
        0, page_height, 0, band_bottom,
        [NAVY_900, NAVY_800],
        positions=[0.0, 1.0],
        extend=True,
    )
    canvas.restoreState()

    # Mark
    logo_y = band_bottom + (BAND_HEIGHT - LOGO_SIZE) / 2.0
    draw_logo(canvas, LOGO_INSET, logo_y, LOGO_SIZE)

    # Wordmark
    text_x = LOGO_INSET + LOGO_SIZE + 11
    mid = band_bottom + BAND_HEIGHT / 2.0
    draw_tracked_string(
        canvas, text_x, mid + 1.5, WORDMARK,
        FONT_HEADING, 10.5, INK_100, tracking=0.42,      # 0.04em
    )
    draw_tracked_string(
        canvas, text_x, mid - 9, WORDMARK_SUB,
        FONT_SUBHEADING, 6.5, INK_500, tracking=1.43,    # 0.22em
    )

    # Eyebrow: teal dot + mono label, right-aligned
    baseline = mid - 2.5
    right_edge = page_width - margin
    label_width = tracked_width(canvas, EYEBROW, FONT_MONO, 7.5, 1.05)
    canvas.saveState()
    canvas.setFillColor(TEAL)
    canvas.circle(right_edge - label_width - 9, baseline + 2.4, 2.4, stroke=0, fill=1)
    canvas.restoreState()
    draw_tracked_string(
        canvas, right_edge, baseline, EYEBROW,
        FONT_MONO, 7.5, TEAL, tracking=1.05, align="right",   # 0.14em
    )

    draw_accent_rule(
        canvas, 0, band_bottom - ACCENT_RULE_HEIGHT, page_width
    )
