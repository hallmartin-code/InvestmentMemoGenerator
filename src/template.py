"""Canonical document structure for the TEN Capital one-page memo.

This module is the single source of truth for *what* a memo contains — the
extraction fields pulled from a deck, and the memo sections rendered to PDF.
Both Claude prompts and the PDF renderer are driven from the definitions here,
so changing the document structure means editing this file only.

It defines structure, not content: no company data, no example text.

See templates/memo_structure.md for the human-readable version.
"""

import re

# --- Header block (page 1 only) ----------------------------------------------
# Field name -> the extraction key it is populated from.

HEADER_FIELDS = {
    "title": "company_name",     # TITLE style, centered
    "subtitle": "tagline",       # BODY style, centered italic, one line below
}


# --- Extraction fields -------------------------------------------------------
# Every field the app pulls out of a source deck, in prompt order.
#   key     — JSON key returned by the extraction call
#   type    — JSON type expected (null when absent from the deck)
#   note    — inline guidance shown to the model; None emits no comment

EXTRACTION_FIELDS = [
    {"key": "company_name",   "type": "string", "note": None},
    {"key": "tagline",        "type": "string", "note": "one sentence, what they do"},
    {"key": "problem",        "type": "string", "note": "2-3 sentences max"},
    {"key": "solution",       "type": "string", "note": "2-3 sentences max"},
    {"key": "business_model", "type": "string", "note": "how they make money"},
    {"key": "traction",       "type": "string", "note": "metrics, milestones, revenue if present"},
    {"key": "market",         "type": "string", "note": "TAM/SAM or market framing"},
    {"key": "team",           "type": "string", "note": "key founders and relevant background"},
    {"key": "ask",            "type": "string", "note": "raise amount, use of funds"},
    {"key": "stage",          "type": "string", "note": "pre-seed / seed / Series A etc."},
    {"key": "risks",          "type": "string", "note": "key risks or open questions you notice"},
    {"key": "notable",        "type": "string", "note": "anything that stood out — positive or negative"},
]

EXTRACTION_KEYS = [field["key"] for field in EXTRACTION_FIELDS]

# Column the // comments align to in the generated JSON schema block.
_COMMENT_COLUMN = 34


# --- Memo sections -----------------------------------------------------------
# The document body, in render order. Every section is optional — one is
# emitted only when the deck supports it — but when present it must appear in
# this order and under this exact header.
#   name    — ALL CAPS header as it appears in the memo and the PDF
#   purpose — what this section is for (documentation; not sent to the model)

MEMO_SECTIONS = [
    {
        "name": "EXECUTIVE SUMMARY",
        "purpose": "What the company does, stage, headline metrics, and what "
                   "they are raising. Written for a partner who has not seen "
                   "the deck.",
    },
    {
        "name": "BIG PICTURE ASSESSMENT",
        "purpose": "The thesis-level read: is the wedge real, and what does "
                   "the deck fail to establish?",
    },
    {
        "name": "WHAT WORKS",
        "purpose": "The strongest specific evidence for investing — traction, "
                   "retention, team credentials, structural advantages.",
    },
    {
        "name": "WHAT DOESN'T",
        "purpose": "Concrete weaknesses in the business or the deck, stated "
                   "plainly. Gaps in team, pricing, positioning, or evidence.",
    },
    {
        "name": "KEY RISKS & OPEN QUESTIONS",
        "purpose": "Risks material enough to change the decision, and the "
                   "questions that remain unresolved from the materials.",
    },
    {
        "name": "RECOMMENDED NEXT STEPS",
        "purpose": "The specific diligence actions or materials needed before "
                   "this can advance.",
    },
    {
        "name": "FINAL INVESTOR TAKE",
        "purpose": "The call — advance, request more, or pass — and the single "
                   "reason behind it.",
    },
]

SECTION_NAMES = [section["name"] for section in MEMO_SECTIONS]


def normalize_section_name(text):
    """Canonical key for comparing section headers.

    Models vary the surface form — curly apostrophes, a trailing colon, title
    case, stray whitespace — so comparison happens on a normalized key rather
    than the literal string.
    """
    text = (text or "").replace("’", "'").replace("‘", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[\s:]+$", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.upper()


_SECTION_LOOKUP = {normalize_section_name(n): n for n in SECTION_NAMES}
_SECTION_ORDER = {
    normalize_section_name(name): index
    for index, name in enumerate(SECTION_NAMES)
}


def match_section_name(text):
    """Return the canonical section name for `text`, or None if unknown."""
    return _SECTION_LOOKUP.get(normalize_section_name(text))


# --- Prompt fragments generated from the definitions above -------------------

def extraction_schema_block():
    """Render EXTRACTION_FIELDS as the JSON schema block for the prompt."""
    lines = ["{"]
    for index, field in enumerate(EXTRACTION_FIELDS):
        last = index == len(EXTRACTION_FIELDS) - 1
        entry = f'  "{field["key"]}": {field["type"]}' + ("" if last else ",")
        if field["note"]:
            entry = entry.ljust(_COMMENT_COLUMN) + f'// {field["note"]}'
        lines.append(entry)
    lines.append("}")
    return "\n".join(lines)


def section_list_block():
    """Render SECTION_NAMES as the section list for the writing prompt."""
    return "\n".join(SECTION_NAMES)


# --- Helpers used by the renderer --------------------------------------------

def order_sections(sections):
    """Sort parsed (name, body) pairs into canonical order.

    Sections not in the template keep their relative position at the end
    rather than being dropped — an unexpected header is still content.
    """
    def rank(section):
        return _SECTION_ORDER.get(normalize_section_name(section[0]))

    known = [s for s in sections if rank(s) is not None]
    unknown = [s for s in sections if rank(s) is None]
    known.sort(key=rank)
    return known + unknown


def unknown_section_names(sections):
    """Return header names that are not part of the canonical structure."""
    return [
        s[0]
        for s in sections
        if s[0] and normalize_section_name(s[0]) not in _SECTION_ORDER
    ]


def blank_structured_data():
    """An empty structured-data dict with every extraction key set to None."""
    return {key: None for key in EXTRACTION_KEYS}
