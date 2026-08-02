"""ReportLab renderer: memo text -> formatted one-page PDF."""

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
)

import brand
import layout

# An ALL-CAPS line ending in a colon starts a new section. Body text may follow
# on the same line or on the lines beneath it.
SECTION_HEADER_RE = re.compile(r"^([A-Z][A-Z0-9 &'’/()\-\.]*):\s*(.*)$")


def parse_memo_sections(memo_text):
    """Split raw memo text into [(section_name, body_text), ...].

    Anything before the first header is dropped — the model is instructed to
    open with a section header, and a stray preamble does not belong in print.
    """
    sections = []
    current_name = None
    current_lines = []

    for line in memo_text.splitlines():
        stripped = line.strip()
        match = SECTION_HEADER_RE.match(stripped)
        # Require a real header: no lowercase letters, at least two characters.
        if match and len(match.group(1).strip()) >= 2:
            if current_name is not None:
                sections.append((current_name, "\n".join(current_lines).strip()))
            current_name = match.group(1).strip()
            current_lines = [match.group(2)] if match.group(2) else []
        elif current_name is not None:
            current_lines.append(stripped)

    if current_name is not None:
        sections.append((current_name, "\n".join(current_lines).strip()))

    return sections


def _clean(text):
    """Strip markdown artifacts and escape XML for ReportLab's mini-markup."""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    return escape(text.strip())


def _paragraphs(body_text):
    """Split a section body into paragraphs on blank lines."""
    blocks = re.split(r"\n\s*\n", body_text)
    return [re.sub(r"\s*\n\s*", " ", b).strip() for b in blocks if b.strip()]


def _draw_footer(canvas, doc):
    """PageTemplate onPage callback: footer rule and left-aligned footer text.

    The right-aligned "PAGE X OF Y" is drawn by NumberedCanvas, which is the
    only place the total page count is known.
    """
    canvas.saveState()
    rule_y = layout.FOOTER_BASELINE + layout.FOOTER_RULE_OFFSET
    canvas.setStrokeColor(brand.RULE_COLOR)
    canvas.setLineWidth(layout.FOOTER_RULE_WIDTH)
    canvas.line(
        layout.MARGIN,
        rule_y,
        layout.PAGE_SIZE[0] - layout.MARGIN,
        rule_y,
    )
    canvas.restoreState()
    brand.draw_tracked_string(
        canvas,
        layout.MARGIN,
        layout.FOOTER_BASELINE,
        layout.FOOTER_LEFT_TEXT,
        layout.FOOTER_FONT_NAME,
        layout.FOOTER_FONT_SIZE,
        brand.FOOTER_COLOR,
        tracking=brand.FOOTER_CHAR_SPACE,
    )


def _draw_first_page(canvas, doc):
    """First page: brand masthead above the frame, plus the standard footer."""
    brand.draw_masthead(
        canvas, layout.PAGE_SIZE[0], layout.PAGE_SIZE[1], layout.MARGIN
    )
    _draw_footer(canvas, doc)


class NumberedCanvas(pdfcanvas.Canvas):
    """Two-pass canvas so the footer can say "Page X of Y"."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(total)
            super().showPage()
        super().save()

    def _draw_page_number(self, total):
        brand.draw_tracked_string(
            self,
            layout.PAGE_SIZE[0] - layout.MARGIN,
            layout.FOOTER_BASELINE,
            f"PAGE {self._pageNumber} OF {total}",
            layout.FOOTER_FONT_NAME,
            layout.FOOTER_FONT_SIZE,
            brand.FOOTER_COLOR,
            tracking=brand.FOOTER_CHAR_SPACE,
            align="right",
        )


def build_pdf(output_path, company_name, tagline, sections):
    """Render the memo to a PDF at output_path."""
    layout.register_fonts()
    styles = layout.build_styles()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=layout.MARGIN,
        rightMargin=layout.MARGIN,
        topMargin=layout.MARGIN,
        bottomMargin=layout.MARGIN,
        title=f"{company_name} — Investment Memo" if company_name else "Investment Memo",
        author="TEN Capital",
    )
    def _frame(height, frame_id):
        return Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            height,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id=frame_id,
        )

    # The masthead is full-bleed and sits mostly inside the top margin, so it
    # costs the first page only a few points of content height.
    first_frame_top = layout.PAGE_SIZE[1] - brand.band_total_height()
    doc.addPageTemplates([
        PageTemplate(
            id="first",
            frames=[_frame(first_frame_top - doc.bottomMargin, "body_first")],
            onPage=_draw_first_page,
        ),
        PageTemplate(
            id="later",
            frames=[_frame(doc.height, "body_later")],
            onPage=_draw_footer,
        ),
    ])

    story = [NextPageTemplate("later")]

    if company_name:
        story.append(Paragraph(_clean(company_name), styles["TITLE"]))
    if tagline:
        story.append(Spacer(1, 1))
        story.append(Paragraph(_clean(tagline), styles["TAGLINE"]))
    if company_name or tagline:
        story.append(Spacer(1, layout.GAP_AFTER_TITLE_BLOCK))

    rendered = 0
    for section_name, body_text in sections:
        if not body_text:
            continue
        story.append(Paragraph(_clean(section_name.upper()), styles["SECTION_HEADER"]))
        story.append(Spacer(1, layout.GAP_AFTER_HEADER))
        for paragraph in _paragraphs(body_text):
            story.append(Paragraph(_clean(paragraph), styles["BODY"]))
        story.append(Spacer(1, layout.GAP_AFTER_SECTION))
        rendered += 1

    if rendered == 0:
        raise ValueError("Nothing to render: the memo contained no sections.")

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
