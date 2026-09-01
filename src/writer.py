"""ReportLab renderer: memo text -> formatted multi-page PDF.

The memo arrives as text with two heading levels and bulleted bodies. Parsing
turns it into

    [{"name": "PROBLEM STATEMENT", "blocks": [
        {"kind": "sub",    "text": "Who Experiences the Problem"},
        {"kind": "para",   "text": "..."},
        {"kind": "bullet", "text": "..."},
    ]}, ...]

and rendering walks that structure. Detection is deliberately tolerant, because
models vary the surface form of a heading far more than they vary its wording.
"""

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

# Heading detection has to survive the surface forms models actually emit: with
# or without a trailing colon, wrapped in **bold**, prefixed with ##, numbered,
# or in title case.
_MD_HEADING_RE = re.compile(r"^\s*(#{1,6})\s*")
_BULLET_RE = re.compile(r"^\s*[-*•·]\s+")
_MD_EMPHASIS_RE = re.compile(r"\*\*|__|\*")

# Fallback for a section heading the template does not define. Deliberately
# strict: an all-caps line, no sentence punctuation, and either multi-word or
# long enough that it cannot be a stray label like "ARR:" at the head of a line.
_GENERIC_HEADER_RE = re.compile(r"^[A-Z][A-Z0-9 &'’/()\-\.,]{1,59}$")

# "Round: common equity" — a short leading label, set bold in the reference.
# Capped in length so a full sentence containing a colon is not mistaken for one.
_LABEL_RE = re.compile(r"^([A-Z][^:]{0,44}?):\s+(\S.*)$")

BULLET_CHAR = "•"


def _strip_markup(text):
    return _MD_EMPHASIS_RE.sub("", text).strip()


def _looks_like_section(text):
    text = text.strip()
    if not _GENERIC_HEADER_RE.match(text):
        return False
    if text.endswith((".", ",")):
        return False
    return " " in text or len(text) >= 8


def _classify(line):
    """Return (kind, text) for one line.

    kind is "section", "sub", "bullet", or "text".
    """
    raw = line.strip()
    if not raw:
        return None, ""

    heading = _MD_HEADING_RE.match(raw)
    hashes = len(heading.group(1)) if heading else 0
    body = _strip_markup(_MD_HEADING_RE.sub("", raw))
    if not body:
        return None, ""

    # An explicit markdown level wins outright: ### and deeper is a subsection,
    # ## and shallower is a section.
    if hashes:
        body = re.sub(r"[\s:]+$", "", body)
        if hashes >= 3:
            return "sub", template.match_subsection_name(body) or body
        return "section", template.match_section_name(body) or body

    if _BULLET_RE.match(raw):
        return "bullet", _strip_markup(_BULLET_RE.sub("", raw))

    # Unprefixed: match against the template before falling back to shape.
    candidate = re.sub(r"[\s:]+$", "", body)
    canonical = template.match_section_name(candidate)
    if canonical:
        return "section", canonical
    canonical = template.match_subsection_name(candidate)
    if canonical:
        return "sub", canonical

    # A heading-shaped line with no body after the colon is still a heading;
    # "LABEL: value" is not.
    head, separator, tail = candidate.partition(":")
    if separator and tail.strip():
        return "text", body
    if _looks_like_section(head):
        return "section", head.strip()

    return "text", body


def parse_memo_sections(memo_text):
    """Split raw memo text into the section/block structure described above.

    Anything before the first section heading is dropped — the model is told to
    open with one, and a stray preamble does not belong in print.
    """
    sections = []
    current = None
    paragraph_lines = []

    def flush_paragraph():
        if paragraph_lines and current is not None:
            joined = " ".join(paragraph_lines).strip()
            if joined:
                current["blocks"].append({"kind": "para", "text": joined})
        paragraph_lines.clear()

    for line in memo_text.splitlines():
        kind, text = _classify(line)

        if kind is None:            # blank line ends a paragraph
            flush_paragraph()
            continue

        if kind == "section":
            flush_paragraph()
            current = {"name": text, "blocks": []}
            sections.append(current)
            continue

        if current is None:
            continue

        if kind == "sub":
            flush_paragraph()
            current["blocks"].append({"kind": "sub", "text": text})
        elif kind == "bullet":
            flush_paragraph()
            current["blocks"].append({"kind": "bullet", "text": text})
        else:
            paragraph_lines.append(text)

    flush_paragraph()

    # A heading with nothing under it is noise, not a section.
    return [s for s in sections if any(b["kind"] != "sub" for b in s["blocks"])]


def sections_or_fallback(memo_text):
    """Parse sections, falling back to one untitled block.

    Returns (sections, degraded). If Claude ignored the heading format entirely
    the prose is still worth rendering — the tokens are already spent and a
    memo without headings beats no memo at all.
    """
    sections = parse_memo_sections(memo_text)
    if sections:
        return sections, False

    body = (memo_text or "").strip()
    if not body:
        return [], False

    blocks = [
        {"kind": "para", "text": re.sub(r"\s*\n\s*", " ", block).strip()}
        for block in re.split(r"\n\s*\n", body)
        if block.strip()
    ]
    return [{"name": "", "blocks": blocks}], True


def sections_as_text(sections):
    """Flatten to [(section_name, plain_text), ...] for the email body."""
    flattened = []
    for section in sections:
        lines = []
        for block in section["blocks"]:
            if block["kind"] == "sub":
                lines.append("")
                lines.append(f"{block['text']}")
            elif block["kind"] == "bullet":
                lines.append(f"  - {block['text']}")
            else:
                lines.append("")
                lines.append(block["text"])
        text = "\n".join(lines).strip()
        if text:
            flattened.append((template.numbered_heading(section["name"])
                              if section["name"] else "", text))
    return flattened


def _clean(text):
    """Strip markdown artifacts and escape XML for ReportLab's mini-markup."""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    return escape(text.strip())


def _with_label(text):
    """Bold a leading "Label:" the way the reference memo does."""
    match = _LABEL_RE.match(text.strip())
    if not match:
        return _clean(text)
    label, rest = match.groups()
    return f"<b>{_clean(label)}:</b> {_clean(rest)}"


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


def _header_story(styles, company_name, tagline, meta_lines):
    """Title, tagline, and the two bold-labelled metadata blocks."""
    story = []
    if company_name:
        title = f"{company_name} {template.TITLE_SUFFIX}"
        story.append(Paragraph(_clean(title), styles["TITLE"]))
    if tagline:
        story.append(Spacer(1, 2))
        story.append(Paragraph(_clean(tagline), styles["TAGLINE"]))

    for index, group in enumerate(meta_lines):
        if not group:
            continue
        story.append(Spacer(1, layout.GAP_AFTER_META_BLOCK if index else
                            layout.GAP_AFTER_TITLE_BLOCK))
        for label, value in group:
            story.append(
                Paragraph(
                    f"<b>{_clean(label)}:</b> {_clean(value)}", styles["META"]
                )
            )
    return story


def _section_story(section, styles):
    """Flowables for one section, in document order."""
    story = []
    name = section["name"]
    if name:
        # No Spacer after a heading — the style's spaceAfter does that job, and
        # a Spacer here would satisfy keepWithNext and strand the heading.
        story.append(
            Paragraph(
                _clean(template.numbered_heading(name)), styles["SECTION_HEADER"]
            )
        )

    previous = None
    for block in section["blocks"]:
        kind = block["kind"]

        if kind == "sub":
            story.append(
                Paragraph(_clean(block["text"]), styles["SUBSECTION_HEADER"])
            )
        elif kind == "bullet":
            # A list opening straight after a heading already has that
            # heading's spaceAfter beneath it.
            if previous == "para":
                story.append(Spacer(1, layout.GAP_AROUND_LIST))
            story.append(
                Paragraph(
                    _with_label(block["text"]),
                    styles["BULLET"],
                    bulletText=BULLET_CHAR,
                )
            )
        else:
            if previous == "bullet":
                story.append(Spacer(1, layout.GAP_AROUND_LIST))
            story.append(Paragraph(_with_label(block["text"]), styles["BODY"]))

        previous = kind

    return story


def build_pdf(output_path, company_name, tagline, sections, meta_lines=()):
    """Render the memo to a PDF at output_path.

    meta_lines is a sequence of groups, each a list of (label, value) pairs,
    rendered as the bold-labelled header blocks beneath the title.
    """
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
    story.extend(_header_story(styles, company_name, tagline, meta_lines))

    rendered = 0
    for section in sections:
        if not any(b["kind"] != "sub" for b in section["blocks"]):
            continue
        story.extend(_section_story(section, styles))
        rendered += 1

    if rendered == 0:
        raise ValueError("Nothing to render: the memo contained no sections.")

    story.append(Spacer(1, layout.GAP_BEFORE_SECTION))
    story.append(Paragraph(_clean(template.CLOSING_LINE), styles["CLOSING"]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
