# TEN Capital — One-Page Investment Memo: Document Structure

The canonical structure for every memo the app generates. Structure only — no
company content, no example text.

The machine-readable version lives in [`src/template.py`](../src/template.py),
which drives both Claude prompts and the PDF renderer. Brand values — palette,
typefaces, marks — live in [`src/brand.py`](../src/brand.py). Edit those files to
change structure or branding; this document is their written counterpart.

---

## 1. Page setup

| Property | Value |
| --- | --- |
| Page size | US Letter, 8.5 × 11 in |
| Margins | 1 in (72 pt) all sides |
| Usable area | 6.5 × 9 in |
| Target length | One page |
| Page background | White (the brand's dark UI theme is not reversed for print) |

## 2. Palette

Transcribed from the TEN Capital Deck Analyzer reference page.

| Token | Hex | Used for |
| --- | --- | --- |
| `NAVY_950` | `#0B1526` | Company name, section headers |
| `NAVY_900` | `#101E33` | Body copy; masthead band (top of gradient) |
| `NAVY_800` | `#16283F` | Masthead band (bottom of gradient) |
| `CORAL` | `#EE5A4E` | Accent rule (left), logo figure |
| `AMBER` | `#F3A22A` | Accent rule (centre), logo figure |
| `TEAL` | `#35BEBB` | Accent rule (right), eyebrow, logo figure |
| `INK_100` | `#F3F6FA` | Wordmark on navy |
| `INK_300` | `#C4D0E0` | Footer hairline |
| `INK_500` | `#7E90A8` | Wordmark subtitle on navy |
| `INK_600` | `#5C6E86` | Tagline, footer text |

## 3. Type scale

| Style | Font | Size | Leading | Colour |
| --- | --- | --- | --- | --- |
| TITLE | Sora Bold | 15 pt | 20 pt | `NAVY_950` |
| TAGLINE | Inter Regular | 9.5 pt | 14 pt | `INK_600` |
| SECTION_HEADER | Sora SemiBold | 10 pt | 14 pt | `NAVY_950` |
| BODY | Inter Regular | 9 pt | 13 pt | `NAVY_900` |
| FOOTER | JetBrains Mono Medium | 7.5 pt | 10 pt | `INK_600` |

## 4. Masthead — first page only

Full-bleed, sits in the top margin so it costs the page only ~8 pt of content
height.

| Element | Spec |
| --- | --- |
| Band | Full page width, 54 pt tall, vertical gradient `NAVY_900` → `NAVY_800` |
| Logo mark | Tri-figure mark, 26 pt, 40 pt from the left edge, vertically centred |
| Wordmark | "TEN CAPITAL", Sora Bold 10.5 pt, `INK_100`, 0.04em tracking |
| Wordmark subtitle | "NETWORK", Sora SemiBold 6.5 pt, `INK_500`, 0.22em tracking |
| Eyebrow | Teal dot + "INVESTMENT MEMO", JetBrains Mono 7.5 pt, `TEAL`, 0.14em tracking, right-aligned to the margin |
| Accent rule | 2.5 pt, full bleed, directly beneath the band, gradient `CORAL` → `AMBER` → `TEAL` |

## 5. Title block — first page only

| Element | Source field | Style | Placement |
| --- | --- | --- | --- |
| Company name | `company_name` | TITLE | Left-aligned |
| Tagline | `tagline` | TAGLINE | Left-aligned, directly below the title |

Omitted entirely when neither field is present.

## 6. Fields extracted from the source deck

Pulled from the deck before any prose is written. A field with no clear support
in the deck is `null` — it is never inferred or filled with a placeholder.

| # | Field | What it captures |
| --- | --- | --- |
| 1 | `company_name` | Company name as stated |
| 2 | `tagline` | One sentence: what they do |
| 3 | `problem` | The problem being solved (2–3 sentences max) |
| 4 | `solution` | The approach or mechanism (2–3 sentences max) |
| 5 | `business_model` | How revenue is generated |
| 6 | `traction` | Metrics, milestones, revenue where present |
| 7 | `market` | TAM/SAM or market framing |
| 8 | `team` | Key founders and relevant background |
| 9 | `ask` | Raise amount and use of funds |
| 10 | `stage` | Pre-seed / seed / Series A etc. |
| 11 | `risks` | Key risks or open questions observed |
| 12 | `notable` | Anything that stood out, positive or negative |

## 7. Memo body — section structure

Each section is a header followed by a body. Every section is **optional** — one
appears only when the deck supports it — but a section that does appear must use
this exact header and this order.

| Order | Section header | Purpose | Draws primarily on |
| --- | --- | --- | --- |
| 1 | `EXECUTIVE SUMMARY` | What the company does, stage, headline metrics, and the raise. Written for a partner who has not seen the deck. | `tagline`, `stage`, `traction`, `ask` |
| 2 | `BIG PICTURE ASSESSMENT` | Thesis-level read: is the wedge real, and what does the deck fail to establish? | `problem`, `solution`, `market` |
| 3 | `WHAT WORKS` | Strongest specific evidence for investing — traction, retention, team, structural advantage. | `traction`, `team`, `business_model` |
| 4 | `WHAT DOESN'T` | Concrete weaknesses in the business or the deck, stated plainly. | `risks`, `team`, `business_model` |
| 5 | `KEY RISKS & OPEN QUESTIONS` | Risks material enough to change the decision, plus what the materials leave unresolved. | `risks`, `notable` |
| 6 | `RECOMMENDED NEXT STEPS` | Specific diligence actions or materials needed before this advances. | `risks`, gaps across all fields |
| 7 | `FINAL INVESTOR TAKE` | The call — advance, request more, or pass — and the single reason behind it. | Synthesis of all above |

Headers are matched case-insensitively and tolerate a missing trailing colon,
markdown emphasis, `#` prefixes, and curly apostrophes. A memo with no
recognisable headers renders as one untitled block.

### Section rendering

```
SECTION HEADER          SECTION_HEADER style, ALL CAPS, left-aligned
                        4 pt gap
Body paragraph.         BODY style, left-aligned, full width
Body paragraph.         2–4 lines each; blank line starts a new paragraph
                        10 pt gap before the next section
```

## 8. Footer — every page

```
TEN CAPITAL — CONFIDENTIAL                              PAGE X OF Y
```

- 0.5 pt `INK_300` hairline, 14 pt above the footer baseline, margin to margin
- Left string and right-aligned page number share the baseline
- FOOTER style, uppercase, 0.4 pt letter-spacing

## 9. Content rules

- Plain text only. No markdown, asterisks, bullet symbols, or decorative em-dashes.
- No citations, footnotes, meta-commentary, or emoji.
- Only real extracted data. A section with no supporting content is omitted
  rather than filled with placeholder text.
- Where the source is insufficient, say so plainly in the body:
  "This section is unclear because…".
