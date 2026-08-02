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
import template

# Header detection has to survive the surface forms models actually emit: with
# or without a trailing colon, wrapped in **bold**, prefixed with ##, or in
# title case. The trailing colon in particular is dropped often enough that
# requiring it left nothing to render.
_MD_HEADING_RE = re.compile(r"^\s*#{1,6}\s*")
_BULLET_RE = re.compile(r"^\s*[-*•]\s+")
_MD_EMPHASIS_RE = re.compile(r"\*\*|__|\*")

# Fallback for a header the template does not define. Deliberately strict: an
# all-caps line, no sentence punctuation, and either multi-word or long enough
# that it cannot be a stray label like "ARR:" at the head of a body line.
_GENERIC_HEADER_RE = re.compile(r"^[A-Z][A-Z0-9 &'’/()\-\.,]{1,59}$")


def _looks_like_header(text):
    text = text.strip()
    if not _GENERIC_HEADER_RE.match(text):
        return False
    if text.endswith((".", ",")):
        return False
    return " " in text or len(text) >= 8


def _split_header(line):
    """Return (header, inline_body) if `line` starts a section, else None."""
    stripped = _MD_HEADING_RE.sub("", line.strip())
    stripped = _BULLET_RE.sub("", stripped)
    stripped = _MD_EMPHASIS_RE.sub("", stripped).strip()
    if not stripped:
        return None

    # "HEADER: body on the same line"
    head, separator, tail = stripped.partition(":")
    if separator:
        canonical = template.match_section_name(head)
        if canonical:
            return canonical, tail.strip()
        if _looks_like_header(head):
            return head.strip(), tail.strip()
        # A colon mid-sentence is not a section break.
        return None

    canonical = template.match_section_name(stripped)
    if canonical:
        return canonical, ""
    if _looks_like_header(stripped):
        return stripped, ""
    return None


def parse_memo_sections(memo_text):
    """Split raw memo text into [(section_name, body_text), ...].

    Anything before the first header is dropped — the model is instructed to
    open with a section header, and a stray preamble does not belong in print.
    """
    sections = []
    current_name = None
    current_lines = []

    for line in memo_text.splitlines():
        header = _split_header(line)
        if header is not None:
            if current_name is not None:
                sections.append((current_name, "\n".join(current_lines).strip()))
            current_name, inline_body = header
            current_lines = [inline_body] if inline_body else []
        elif current_name is not None:
            current_lines.append(line.strip())

    if current_name is not None:
        sections.append((current_name, "\n".join(current_lines).strip()))

    return [(name, body) for name, body in sections if body]


def sections_or_fallback(memo_text):
    """Parse sections, falling back to one untitled block.

    Returns (sections, degraded). If Claude ignored the header format entirely
    the prose is still worth rendering — the tokens are already spent and a
    memo without headers beats no memo at all.
    """
    sections = parse_memo_sections(memo_text)
    if sections:
        return sections, False

    body = (memo_text or "").strip()
    if not body:
        return [], False
    return [("", body)], True


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
        # An empty name is the untitled fallback block — render body only.
        if section_name:
            story.append(
                Paragraph(_clean(section_name.upper()), styles["SECTION_HEADER"])
            )
            story.append(Spacer(1, layout.GAP_AFTER_HEADER))
        for paragraph in _paragraphs(body_text):
            story.append(Paragraph(_clean(paragraph), styles["BODY"]))
        story.append(Spacer(1, layout.GAP_AFTER_SECTION))
        rendered += 1

    if rendered == 0:
        raise ValueError("Nothing to render: the memo contained no sections.")

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
