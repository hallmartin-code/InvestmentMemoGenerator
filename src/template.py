"""Canonical document structure for the TEN Capital investment memo.

This module is the single source of truth for *what* a memo contains — the
extraction fields pulled from a deck, and the numbered sections and subsections
rendered to PDF. Both Claude prompts and the PDF renderer are driven from the
definitions here, so changing the document structure means editing this file
only.

It defines structure, not content: no company data, no example text.

The structure follows the TEN Capital house memo: a metadata header block, then
fifteen numbered sections, each made of named subsections whose bodies are
either prose or bullets. See templates/memo_structure.md for the human-readable
version.
"""

import re
from datetime import date

# --- Header block (page 1 only) ----------------------------------------------
# The masthead metadata, rendered as "Label: value" lines under the title.
#   label  — printed label, set bold
#   key    — extraction key it is populated from, or None when computed
#   block  — 1 or 2; the two groups are separated by a blank line

HEADER_META = [
    {"label": "Prepared by", "key": None, "block": 1},   # always TEN Capital Network
    {"label": "Date", "key": None, "block": 1},          # generation date
    {"label": "Deal Stage", "key": "deal_stage", "block": 1},
    {"label": "Proposed Investment", "key": "proposed_investment", "block": 1},
    {"label": "Company", "key": "company_name", "block": 2},
    {"label": "Primary Asset", "key": "primary_asset", "block": 2},
    {"label": "Stage", "key": "stage", "block": 2},
    {"label": "Sector", "key": "sector", "block": 2},
]

PREPARED_BY = "TEN Capital Network"

# Field name -> the extraction key it is populated from. Retained because the
# CLI and web app read the document title and subtitle through it.
HEADER_FIELDS = {
    "title": "company_name",
    "subtitle": "tagline",
}

TITLE_SUFFIX = "Investment Memo"


# --- Extraction fields -------------------------------------------------------
# Every field the app pulls out of a source deck, in prompt order. These stay
# close to what a deck actually states — analysis (thesis, risk framing, return
# scenarios, the recommendation) is the writing call's job, not extraction.
#   key     — JSON key returned by the extraction call
#   type    — JSON type expected (null when absent from the deck)
#   note    — inline guidance shown to the model; None emits no comment

EXTRACTION_FIELDS = [
    {"key": "company_name",        "type": "string", "note": None},
    {"key": "tagline",             "type": "string", "note": "one sentence, what they do"},
    {"key": "sector",              "type": "string", "note": "sector / sub-sector"},
    {"key": "stage",               "type": "string", "note": "pre-seed / seed / Series A / clinical phase"},
    {"key": "primary_asset",       "type": "string", "note": "lead product, asset, or platform"},
    {"key": "deal_stage",          "type": "string", "note": "round being raised"},
    {"key": "proposed_investment", "type": "string", "note": "check size or allocation on offer"},
    {"key": "round_structure",     "type": "string", "note": "equity, note, SAFE; terms if stated"},
    {"key": "valuation",           "type": "string", "note": "cap or pre/post-money, with basis"},
    {"key": "capital_remaining",   "type": "string", "note": "how much of the round is still open"},
    {"key": "use_of_proceeds",     "type": "string", "note": "line items if given"},
    {"key": "follow_on_plan",      "type": "string", "note": "next financing planned after this one"},
    {"key": "problem",             "type": "string", "note": "who has it, how severe, how often"},
    {"key": "current_alternatives", "type": "string", "note": "what buyers use today and its limits"},
    {"key": "why_now",             "type": "string", "note": "timing signal — tech, regulatory, market"},
    {"key": "solution",            "type": "string", "note": "how the product works, mechanism"},
    {"key": "differentiation",     "type": "string", "note": "what makes it different from alternatives"},
    {"key": "defensibility",       "type": "string", "note": "IP, patents, exclusivity, moat"},
    {"key": "product_maturity",    "type": "string", "note": "readiness — trial phase, pilot, GA"},
    {"key": "market",              "type": "string", "note": "target market, TAM/SAM/SOM with any stated basis"},
    {"key": "market_dynamics",     "type": "string", "note": "tailwinds, M&A precedent, buyer appetite"},
    {"key": "traction",            "type": "string", "note": "metrics, milestones, revenue, dated if possible"},
    {"key": "leading_indicators",  "type": "string", "note": "early signals the company tracks"},
    {"key": "competitors",         "type": "string", "note": "direct competitors named in the deck"},
    {"key": "indirect_alternatives", "type": "string", "note": "substitutes and adjacent approaches"},
    {"key": "go_to_market",        "type": "string", "note": "initial wedge and expansion path"},
    {"key": "scalability",         "type": "string", "note": "what scaling depends on — partners, supply, hiring"},
    {"key": "team",                "type": "string", "note": "key people and relevant background"},
    {"key": "team_gaps",           "type": "string", "note": "roles unfilled or thin, if apparent"},
    {"key": "financials",          "type": "string", "note": "revenue, burn, runway, unit economics"},
    {"key": "risks",               "type": "string", "note": "risks or open questions you notice"},
    {"key": "notable",             "type": "string", "note": "anything that stood out — positive or negative"},
]

EXTRACTION_KEYS = [field["key"] for field in EXTRACTION_FIELDS]

# Column the // comments align to in the generated JSON schema block.
_COMMENT_COLUMN = 38


# --- Memo sections -----------------------------------------------------------
# The document body, in render order. A section is emitted only when the deck
# supports it, but when present it must appear in this order and under this
# exact header.
#   name        — ALL CAPS header, printed with its 1-based number
#   purpose     — what the section is for (guides the writing prompt)
#   optional    — True for sections that may be dropped entirely
#   subsections — named blocks within the section
#       name    — Title Case subheading
#       body    — "prose" (paragraphs) or "bullets" (a bulleted list)
#       note    — guidance for the writing prompt
#
# A section with no subsections is written as plain paragraphs (body "prose")
# or as a labelled list (body "bullets") directly under its header.

MEMO_SECTIONS = [
    {
        "name": "EXECUTIVE SUMMARY",
        "purpose": "A self-contained one-page read for a partner who has not "
                   "seen the deck.",
        "subsections": [
            {"name": "Company Snapshot", "body": "prose",
             "note": "What the company does, its stage, and where the lead asset stands."},
            {"name": "Deal Terms Summary", "body": "bullets",
             "note": "Round, valuation, capital remaining, planned follow-on, use of proceeds. Label each line."},
            {"name": "One-Sentence Investment Thesis", "body": "prose",
             "note": "A single sentence. The whole case, compressed."},
            {"name": "Key Supporting Facts", "body": "bullets",
             "note": "The strongest specific evidence, drawn from the deck."},
            {"name": "Primary Risks", "body": "bullets",
             "note": "The risks that would change the decision."},
            {"name": "Expected Outcome & Return Profile", "body": "bullets",
             "note": "Base, upside, and downside in one line each. Label each line."},
            {"name": "Final Recommendation", "body": "prose",
             "note": "The call in the opening words, then one line of qualification."},
        ],
    },
    {
        "name": "COMPANY OVERVIEW",
        "purpose": "What the company is building and where it stands today.",
        "subsections": [],
        "body": "prose",
    },
    {
        "name": "PROBLEM STATEMENT",
        "purpose": "Establish that the problem is real, severe, and current.",
        "subsections": [
            {"name": "Who Experiences the Problem", "body": "prose", "note": None},
            {"name": "Severity & Frequency", "body": "bullets", "note": None},
            {"name": "Current Alternatives", "body": "bullets",
             "note": "What is used today, and where each falls short."},
            {"name": "Why This Problem Is Worth Solving Now", "body": "prose",
             "note": "The timing signal — technical, regulatory, or market."},
        ],
    },
    {
        "name": "SOLUTION & PRODUCT",
        "purpose": "How the product works and why it is hard to copy.",
        "subsections": [
            {"name": "Product Functionality", "body": "prose",
             "note": "The mechanism, concretely."},
            {"name": "Differentiation", "body": "bullets", "note": None},
            {"name": "Technical Defensibility", "body": "bullets",
             "note": "IP, exclusivity, know-how, and their duration."},
            {"name": "Product Maturity", "body": "prose",
             "note": "Where it sits on the path to market."},
        ],
    },
    {
        "name": "MARKET OPPORTUNITY",
        "purpose": "Size the opportunity and state the assumptions behind it.",
        "subsections": [
            {"name": "Target Market", "body": "prose", "note": None},
            {"name": "TAM / SAM / SOM (Assumptions)", "body": "bullets",
             "note": "Label each line. Say plainly which figures are assumed rather than sourced."},
            {"name": "Market Dynamics", "body": "prose",
             "note": "Buyer appetite, tailwinds, precedent transactions."},
        ],
    },
    {
        "name": "TRACTION & KEY METRICS",
        "purpose": "What has actually happened, with dates and numbers.",
        "subsections": [
            {"name": "Progress to Date", "body": "bullets",
             "note": "Dated milestones and hard metrics only."},
            {"name": "Leading Indicators", "body": "bullets",
             "note": "Early signals that precede the outcome that matters."},
        ],
    },
    {
        "name": "COMPETITIVE LANDSCAPE",
        "purpose": "Who else is solving this, and what keeps them out.",
        "subsections": [
            {"name": "Direct Competitors", "body": "bullets", "note": None},
            {"name": "Indirect Alternatives", "body": "bullets", "note": None},
            {"name": "Barriers to Entry", "body": "bullets", "note": None},
        ],
    },
    {
        "name": "GO-TO-MARKET STRATEGY",
        "purpose": "The wedge, the expansion path, and what scaling depends on.",
        "subsections": [
            {"name": "Initial Strategy", "body": "bullets", "note": None},
            {"name": "Scalability", "body": "bullets",
             "note": "The dependencies — partners, supply chain, hiring."},
        ],
    },
    {
        "name": "TEAM & EXECUTION RISK",
        "purpose": "Whether this team can do this specific thing.",
        "subsections": [
            {"name": "Strengths", "body": "bullets", "note": None},
            {"name": "Gaps / Risks", "body": "bullets",
             "note": "Missing functions and concentration risk. Be direct."},
        ],
    },
    {
        "name": "FINANCIALS & UNIT ECONOMICS",
        "purpose": "The numbers disclosed, and what has to be assumed.",
        "subsections": [
            {"name": "Disclosed", "body": "bullets",
             "note": "Only figures the deck actually states."},
            {"name": "Assumption", "body": "prose",
             "note": "What you infer, flagged as inference."},
        ],
    },
    {
        "name": "DEAL TERMS & STRUCTURE",
        "purpose": "The instrument, the price, and the dilution picture.",
        "subsections": [],
        "body": "bullets",
        "note": "Label each line: Security, Valuation, Future dilution, and any "
                "other stated term.",
    },
    {
        "name": "KEY RISKS & OPEN QUESTIONS",
        "purpose": "Risks grouped by type, so none is quietly omitted.",
        "subsections": [
            {"name": "Market Risks", "body": "bullets", "note": None},
            {"name": "Execution Risks", "body": "bullets", "note": None},
            {"name": "Technology Risks", "body": "bullets", "note": None},
            {"name": "Financing Risks", "body": "bullets", "note": None},
        ],
    },
    {
        "name": "INVESTMENT THESIS",
        "purpose": "The belief, its preconditions, and its kill criteria.",
        "subsections": [
            {"name": "Core Belief", "body": "prose",
             "note": "One or two sentences. The non-consensus claim."},
            {"name": "What Must Be True", "body": "bullets", "note": None},
            {"name": "What Invalidates the Thesis", "body": "bullets",
             "note": "Concrete, observable outcomes that would end it."},
        ],
    },
    {
        "name": "EXPECTED OUTCOMES & RETURN SCENARIOS",
        "purpose": "Three scenarios with return multiples and a time horizon.",
        "subsections": [
            {"name": "Downside Case", "body": "bullets",
             "note": "Include a Return: line."},
            {"name": "Base Case", "body": "bullets",
             "note": "Include a Return: line."},
            {"name": "Upside Case", "body": "bullets",
             "note": "Include a Return: line."},
            {"name": "Timeframe", "body": "bullets",
             "note": "Time to a liquidity-relevant event."},
        ],
    },
    {
        "name": "FINAL DECISION & RATIONALE",
        "purpose": "The call and the terms on which it is made.",
        "subsections": [],
        "body": "bullets",
        "note": "Label each line: Recommendation, Check Size, Conviction, "
                "Follow-On Strategy.",
    },
    {
        "name": "POST-INVESTMENT MONITORING FRAMEWORK",
        "purpose": "What to watch after the wire, and what would trigger more.",
        "optional": True,
        "subsections": [
            {"name": "Metrics to Track", "body": "bullets", "note": None},
            {"name": "Thesis Checkpoints", "body": "bullets", "note": None},
            {"name": "Follow-On Conditions", "body": "bullets", "note": None},
        ],
    },
]

SECTION_NAMES = [section["name"] for section in MEMO_SECTIONS]

CLOSING_LINE = "Prepared by TEN Capital"


def section_number(name):
    """1-based number for a canonical section name, or None if unknown."""
    canonical = match_section_name(name)
    if canonical is None:
        return None
    index = SECTION_NAMES.index(canonical)
    return None if MEMO_SECTIONS[index].get("optional") else index + 1


def numbered_heading(name):
    """Section heading as printed: "3. PROBLEM STATEMENT"."""
    canonical = match_section_name(name) or name
    number = section_number(canonical)
    return f"{number}. {canonical}" if number else canonical


def subsection_names(section_name):
    """Canonical subsection names for a section, in order."""
    canonical = match_section_name(section_name)
    if canonical is None:
        return []
    index = SECTION_NAMES.index(canonical)
    return [s["name"] for s in MEMO_SECTIONS[index].get("subsections", [])]


def normalize_section_name(text):
    """Canonical key for comparing headers.

    Models vary the surface form — curly apostrophes, a trailing colon, a
    leading number, title case, stray whitespace — so comparison happens on a
    normalized key rather than the literal string.
    """
    text = (text or "").replace("’", "'").replace("‘", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"^\s*\d+[\.\)]\s*", "", text.strip())
    # The reference titles the first section "1. EXECUTIVE SUMMARY (ONE PAGE)";
    # a trailing parenthetical is a note to the writer, not part of the name.
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    text = re.sub(r"^(OPTIONAL ADD[- ]?ON|OPTIONAL)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"[\s:]+$", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.upper()


_SECTION_LOOKUP = {normalize_section_name(n): n for n in SECTION_NAMES}
_SECTION_ORDER = {
    normalize_section_name(name): index
    for index, name in enumerate(SECTION_NAMES)
}

_SUBSECTION_LOOKUP = {}
for _section in MEMO_SECTIONS:
    for _sub in _section.get("subsections", []):
        _SUBSECTION_LOOKUP.setdefault(
            normalize_section_name(_sub["name"]), _sub["name"]
        )


def match_section_name(text):
    """Return the canonical section name for `text`, or None if unknown."""
    return _SECTION_LOOKUP.get(normalize_section_name(text))


def match_subsection_name(text):
    """Return the canonical subsection name for `text`, or None if unknown."""
    return _SUBSECTION_LOOKUP.get(normalize_section_name(text))


def subsection_body_kind(section_name, subsection_name):
    """"prose" or "bullets" for a subsection, defaulting to prose."""
    canonical = match_section_name(section_name)
    if canonical is None:
        return "prose"
    index = SECTION_NAMES.index(canonical)
    target = normalize_section_name(subsection_name)
    for sub in MEMO_SECTIONS[index].get("subsections", []):
        if normalize_section_name(sub["name"]) == target:
            return sub.get("body", "prose")
    return "prose"


def section_body_kind(section_name):
    """"prose" or "bullets" for a section written without subsections."""
    canonical = match_section_name(section_name)
    if canonical is None:
        return "prose"
    index = SECTION_NAMES.index(canonical)
    return MEMO_SECTIONS[index].get("body", "prose")


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
    """Render the full section outline for the writing prompt.

    Emits the exact header text the writer must produce, so the renderer's
    parser and the model's output agree on the surface form.
    """
    lines = []
    for index, section in enumerate(MEMO_SECTIONS):
        heading = (
            section["name"]
            if section.get("optional")
            else f"{index + 1}. {section['name']}"
        )
        suffix = "   [optional — include only if warranted]" if section.get("optional") else ""
        lines.append(f"## {heading}{suffix}")
        lines.append(f"   Purpose: {section['purpose']}")

        subsections = section.get("subsections", [])
        if not subsections:
            kind = section.get("body", "prose")
            hint = "bulleted lines" if kind == "bullets" else "paragraphs"
            note = section.get("note")
            lines.append(f"   Write as {hint}." + (f" {note}" if note else ""))
            lines.append("")
            continue

        for sub in subsections:
            hint = "bullets" if sub.get("body") == "bullets" else "prose"
            entry = f"### {sub['name']}  ({hint})"
            if sub.get("note"):
                entry += f" — {sub['note']}"
            lines.append(entry)
        lines.append("")

    return "\n".join(lines).rstrip()


# --- Helpers used by the renderer --------------------------------------------

def order_sections(sections):
    """Sort parsed sections into canonical order.

    Accepts either (name, body) pairs or dicts carrying a "name". Sections not
    in the template keep their relative position at the end rather than being
    dropped — an unexpected header is still content.
    """
    def name_of(section):
        return section["name"] if isinstance(section, dict) else section[0]

    def rank(section):
        return _SECTION_ORDER.get(normalize_section_name(name_of(section)))

    known = [s for s in sections if rank(s) is not None]
    unknown = [s for s in sections if rank(s) is None]
    known.sort(key=rank)
    return known + unknown


def unknown_section_names(sections):
    """Return header names that are not part of the canonical structure."""
    def name_of(section):
        return section["name"] if isinstance(section, dict) else section[0]

    return [
        name_of(s)
        for s in sections
        if name_of(s) and normalize_section_name(name_of(s)) not in _SECTION_ORDER
    ]


def today_text(when=None):
    """The memo date as printed: "January 1, 2026".

    Built from the parts rather than a %-d / %#d format string, which differs
    between platforms.
    """
    when = when or date.today()
    return f"{when:%B} {when.day}, {when.year}"


def header_meta_lines(data, date_text=None):
    """Build the header metadata groups as [[(label, value), ...], ...].

    A line whose value is missing is dropped rather than printed empty, so a
    thin deck produces a shorter header rather than a row of blanks.
    """
    date_text = date_text or today_text()
    groups = {}
    for entry in HEADER_META:
        if entry["key"] is None:
            value = PREPARED_BY if entry["label"] == "Prepared by" else date_text
        else:
            value = (data or {}).get(entry["key"])
        value = (value or "").strip() if isinstance(value, str) else value
        if not value:
            continue
        groups.setdefault(entry["block"], []).append((entry["label"], str(value)))
    return [groups[key] for key in sorted(groups)]


def blank_structured_data():
    """An empty structured-data dict with every extraction key set to None."""
    return {key: None for key in EXTRACTION_KEYS}
