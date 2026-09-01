"""Claude API calls: structured extraction from deck text, then memo prose."""

import json
import os
import re

from dotenv import load_dotenv

import template

load_dotenv()

# claude-opus-4-5 is pinned per the project spec. Override with ANTHROPIC_MODEL
# if you want a newer model (e.g. claude-opus-5).
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

# The memo runs to roughly 2,000 words across fifteen sections, so the writing
# call needs far more headroom than a one-pager did.
EXTRACTION_MAX_TOKENS = 4000
WRITING_MAX_TOKENS = 12000

# The schema block and the section list are generated from template.py so the
# document structure has one definition. The rendered prompts are unchanged.
_EXTRACTION_PROMPT_TEMPLATE = """You are extracting structured information from an investor pitch deck for an investment memo.

Return ONLY a JSON object with these keys. If a section has no clear content, use null.

{schema}

Pitch deck text:
{raw_text}"""

EXTRACTION_PROMPT = _EXTRACTION_PROMPT_TEMPLATE.replace(
    "{schema}", template.extraction_schema_block()
)

_WRITING_PROMPT_TEMPLATE = """You are an investment memo writer for TEN Capital.

Write a full investment memo using the structured data below. Follow these rules exactly:

TONE & VOICE
- Write like a real investor explaining their thinking to another partner
- Use plain, direct language — no buzzwords, no hype, no marketing phrases
- Be honest and specific; call out weaknesses clearly
- Vary sentence length to sound natural
- Never sound like AI, consulting jargon, or sales copy
- Short paragraphs (2–4 lines max); no dense text blocks
- Bullets are single lines, not mini-paragraphs

EVIDENCE DISCIPLINE
- The structured data comes from the company's own deck. Facts in it are the company's claims, not verified truth
- Never invent a number, date, name, or citation that is not in the data
- Where the deck gives no basis for a figure, say the figure is assumed rather than sourced
- Where a section has no support in the data, write one line saying what is missing and why it matters, rather than padding
- Sections 12 to 15 are your analysis, not the deck's — form a view and commit to it

DOCUMENT OUTLINE
Write the sections below, in this order, using these exact headings. Omit a
section only if the data supports nothing in it at all.

{sections}

FORMAT
Section headings use two hashes and their number. Subsection headings use three
hashes. Bulleted lines start with "- ". Exactly like this:

## 1. EXECUTIVE SUMMARY
### Company Snapshot
First paragraph of the snapshot.

Second paragraph if the section needs one.

### Deal Terms Summary
- Round: common equity or convertible note
- Pre-money valuation: $50 million

Where a line carries a label, write it as "Label: value" — the renderer sets the
label in bold.

Do not write any preamble before the first heading. Do not add sections that are
not in the outline. Do not restate a heading inside its own body.

RULES
- No markdown beyond the ## / ### headings and "- " bullets — no bold, no italics, no tables
- No citations, no footnotes, no meta-commentary
- No emojis
- Do not explain your process
- The output will be rendered into a PDF — write for print, not for a chat window
- Target length: roughly 1,800–2,400 words across the whole memo

Structured data:
{json_data}"""

WRITING_PROMPT = _WRITING_PROMPT_TEMPLATE.replace(
    "{sections}", template.section_list_block()
)


class APICallError(Exception):
    """Raised when a Claude API call fails."""


class MalformedJSONError(Exception):
    """Raised when the extraction response is not parseable JSON."""

    def __init__(self, raw_response):
        self.raw_response = raw_response
        super().__init__("Could not parse JSON from the extraction response.")


def _client():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise APICallError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add "
            "your key, or export ANTHROPIC_API_KEY in your shell."
        )
    import anthropic

    return anthropic.Anthropic()


def _send(prompt, max_tokens, label):
    """Send a single-turn prompt and return the response text."""
    client = _client()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise APICallError(f"{label} call failed ({type(exc).__name__}): {exc}") from exc

    text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    if not text:
        raise APICallError(
            f"{label} call returned no text "
            f"(stop_reason={response.stop_reason!r})."
        )
    return text


def extract_structured_data(raw_text):
    """First Claude call: raw deck text -> structured dict."""
    # Plain replace, not .format() — the prompt contains literal JSON braces.
    prompt = EXTRACTION_PROMPT.replace("{raw_text}", raw_text)
    response_text = _send(prompt, EXTRACTION_MAX_TOKENS, "Extraction")

    try:
        return json.loads(_strip_code_fence(response_text))
    except (json.JSONDecodeError, ValueError):
        raise MalformedJSONError(response_text) from None


def write_memo(structured_data):
    """Second Claude call: structured dict -> memo prose."""
    json_data = json.dumps(structured_data, indent=2, ensure_ascii=False)
    prompt = WRITING_PROMPT.replace("{json_data}", json_data)
    return _send(prompt, WRITING_MAX_TOKENS, "Memo writing")


def _strip_code_fence(text):
    """Unwrap a ```json ...``` fence if the model added one."""
    fenced = re.match(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    return text
