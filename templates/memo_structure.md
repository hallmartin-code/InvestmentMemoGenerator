# TEN Capital — Investment Memo: Document Structure

The canonical structure for every memo the app generates. Structure only — no
company content, no example text.

The machine-readable version lives in [`src/template.py`](../src/template.py),
which drives both Claude prompts and the PDF renderer. Brand values — palette,
typefaces, marks — live in [`src/brand.py`](../src/brand.py). Edit those files to
change structure or branding; this document is their written counterpart.

The structure is modelled on the TEN Capital house memo: a bold-labelled
metadata header, then fifteen numbered sections built from named subsections
whose bodies are either prose or bullets, and one optional add-on section.

---

## 1. Page setup

| Property | Value |
| --- | --- |
| Page size | US Letter, 8.5 × 11 in |
| Margins | 1 in (72 pt) all sides |
| Usable area | 6.5 × 9 in |
| Target length | 4–8 pages; section 1 is sized to fill exactly one page |
| Page background | White (the brand's dark UI theme is not reversed for print) |

## 2. Palette

Transcribed from the TEN Capital Deck Analyzer reference page.

| Token | Hex | Used for |
| --- | --- | --- |
| `NAVY_950` | `#0B1526` | Title, section headings |
| `NAVY_900` | `#101E33` | Body copy; masthead band (top of gradient) |
| `NAVY_800` | `#16283F` | Masthead band (bottom of gradient) |
| `NAVY_700` | `#1E354F` | Subsection headings |
| `CORAL` | `#EE5A4E` | Accent rule (left), logo figure |
| `AMBER` | `#F3A22A` | Accent rule (centre), logo figure |
| `TEAL` | `#35BEBB` | Accent rule (right), eyebrow, logo figure |
| `INK_100` | `#F3F6FA` | Wordmark on navy |
| `INK_300` | `#C4D0E0` | Footer hairline |
| `INK_500` | `#7E90A8` | Wordmark subtitle on navy |
| `INK_600` | `#5C6E86` | Tagline, closing line, footer text |

## 3. Type scale

The reference memo is set in Open Sans at 11 pt with a 1 : 1.18 : 1.55 : 2.1
ramp from body to H1. That hierarchy is preserved here in the brand typefaces
and at print density, so the memo still reads as a TEN Capital document rather
than a Google Docs export.

| Style | Font | Size | Leading | Colour |
| --- | --- | --- | --- | --- |
| TITLE | Sora Bold | 17 pt | 21 pt | `NAVY_950` |
| TAGLINE | Inter Regular | 9.5 pt | 14 pt | `INK_600` |
| META | Inter Regular | 9 pt | 13 pt | `NAVY_900` |
| SECTION_HEADER | Sora Bold | 12.5 pt | 16 pt | `NAVY_950` |
| SUBSECTION_HEADER | Sora SemiBold | 10.5 pt | 14 pt | `NAVY_700` |
| BODY | Inter Regular | 9.5 pt | 13.5 pt | `NAVY_900` |
| BULLET | Inter Regular | 9.5 pt | 13.5 pt | `NAVY_900` |
| CLOSING | Sora SemiBold | 9 pt | 13 pt | `INK_600` |
| FOOTER | JetBrains Mono Medium | 7.5 pt | 10 pt | `INK_600` |

Inline labels ("**Round:** common equity") are set in **Inter SemiBold** via
ReportLab's `<b>` markup, which the font family registration maps to that
weight.

### Vertical rhythm

The reference puts 12 pt above and below each body paragraph and each bulleted
*list*, but zero between items inside a list. That rhythm is kept, scaled for
print.

| Gap | Points |
| --- | --- |
| Before a section heading | 14 |
| After a section heading | 5 |
| Before a subsection heading | 9 |
| After a subsection heading | 3 |
| After a body paragraph | 5 |
| Between bullets in one list | 0 |
| Around a bulleted list | 4 |
| Title block → first metadata group | 16 |
| Between metadata groups | 8 |

Section and subsection headings are set `keepWithNext`, so a heading never
strands at the foot of a page. No `Spacer` is emitted directly after a heading —
one would satisfy `keepWithNext` and defeat it.

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

## 5. Header block — first page only

| Element | Source | Style |
| --- | --- | --- |
| Title | `company_name` + "Investment Memo" | TITLE |
| Tagline | `tagline` | TAGLINE |

Then two metadata groups, each a run of `Label: value` lines with the label
bold, separated by a blank line:

| Group | Lines |
| --- | --- |
| 1 | Prepared by · Date · Deal Stage · Proposed Investment |
| 2 | Company · Primary Asset · Stage · Sector |

"Prepared by" is always `TEN Capital Network`; "Date" is the generation date.
A line whose value is missing is dropped rather than printed empty, so a thin
deck yields a shorter header instead of a column of blanks.

## 6. Fields extracted from the source deck

Pulled from the deck before any prose is written. A field with no clear support
in the deck is `null` — never inferred, never filled with a placeholder.

These stay close to what a deck actually states. Analysis — the thesis, the risk
framing, the return scenarios, the recommendation — is the writing call's job,
not extraction's.

| # | Field | What it captures |
| --- | --- | --- |
| 1 | `company_name` | Company name as stated |
| 2 | `tagline` | One sentence: what they do |
| 3 | `sector` | Sector / sub-sector |
| 4 | `stage` | Pre-seed / seed / Series A / clinical phase |
| 5 | `primary_asset` | Lead product, asset, or platform |
| 6 | `deal_stage` | Round being raised |
| 7 | `proposed_investment` | Check size or allocation on offer |
| 8 | `round_structure` | Equity, note, SAFE; terms if stated |
| 9 | `valuation` | Cap or pre/post-money, with basis |
| 10 | `capital_remaining` | How much of the round is still open |
| 11 | `use_of_proceeds` | Line items if given |
| 12 | `follow_on_plan` | Next financing planned after this one |
| 13 | `problem` | Who has it, how severe, how often |
| 14 | `current_alternatives` | What buyers use today and its limits |
| 15 | `why_now` | Timing signal — tech, regulatory, market |
| 16 | `solution` | How the product works, mechanism |
| 17 | `differentiation` | What sets it apart from alternatives |
| 18 | `defensibility` | IP, patents, exclusivity, moat |
| 19 | `product_maturity` | Readiness — trial phase, pilot, GA |
| 20 | `market` | Target market, TAM/SAM/SOM with any stated basis |
| 21 | `market_dynamics` | Tailwinds, M&A precedent, buyer appetite |
| 22 | `traction` | Metrics, milestones, revenue, dated where possible |
| 23 | `leading_indicators` | Early signals the company tracks |
| 24 | `competitors` | Direct competitors named in the deck |
| 25 | `indirect_alternatives` | Substitutes and adjacent approaches |
| 26 | `go_to_market` | Initial wedge and expansion path |
| 27 | `scalability` | What scaling depends on — partners, supply, hiring |
| 28 | `team` | Key people and relevant background |
| 29 | `team_gaps` | Roles unfilled or thin, if apparent |
| 30 | `financials` | Revenue, burn, runway, unit economics |
| 31 | `risks` | Risks or open questions observed |
| 32 | `notable` | Anything that stood out, positive or negative |

## 7. Memo body — section structure

Sections are numbered and rendered in this order regardless of the order the
model returns them. Every section is **optional** — one appears only when the
deck supports it — but a section that appears must use this exact heading.

Body kinds: **prose** = paragraphs, **bullets** = a bulleted list.

| # | Section | Subsections (body) |
| --- | --- | --- |
| 1 | `EXECUTIVE SUMMARY` | Company Snapshot (prose) · Deal Terms Summary (bullets) · One-Sentence Investment Thesis (prose) · Key Supporting Facts (bullets) · Primary Risks (bullets) · Expected Outcome & Return Profile (bullets) · Final Recommendation (prose) |
| 2 | `COMPANY OVERVIEW` | — (prose) |
| 3 | `PROBLEM STATEMENT` | Who Experiences the Problem (prose) · Severity & Frequency (bullets) · Current Alternatives (bullets) · Why This Problem Is Worth Solving Now (prose) |
| 4 | `SOLUTION & PRODUCT` | Product Functionality (prose) · Differentiation (bullets) · Technical Defensibility (bullets) · Product Maturity (prose) |
| 5 | `MARKET OPPORTUNITY` | Target Market (prose) · TAM / SAM / SOM (Assumptions) (bullets) · Market Dynamics (prose) |
| 6 | `TRACTION & KEY METRICS` | Progress to Date (bullets) · Leading Indicators (bullets) |
| 7 | `COMPETITIVE LANDSCAPE` | Direct Competitors (bullets) · Indirect Alternatives (bullets) · Barriers to Entry (bullets) |
| 8 | `GO-TO-MARKET STRATEGY` | Initial Strategy (bullets) · Scalability (bullets) |
| 9 | `TEAM & EXECUTION RISK` | Strengths (bullets) · Gaps / Risks (bullets) |
| 10 | `FINANCIALS & UNIT ECONOMICS` | Disclosed (bullets) · Assumption (prose) |
| 11 | `DEAL TERMS & STRUCTURE` | — (bullets, labelled) |
| 12 | `KEY RISKS & OPEN QUESTIONS` | Market Risks · Execution Risks · Technology Risks · Financing Risks (all bullets) |
| 13 | `INVESTMENT THESIS` | Core Belief (prose) · What Must Be True (bullets) · What Invalidates the Thesis (bullets) |
| 14 | `EXPECTED OUTCOMES & RETURN SCENARIOS` | Downside Case · Base Case · Upside Case · Timeframe (all bullets) |
| 15 | `FINAL DECISION & RATIONALE` | — (bullets, labelled) |
| — | `POST-INVESTMENT MONITORING FRAMEWORK` | Metrics to Track · Thesis Checkpoints · Follow-On Conditions (all bullets) |

The monitoring framework is an optional add-on: it carries no number and is
included only when warranted.

Section 1 is written to stand alone — a partner who reads only page one should
be able to act on it.

### The heading contract

The writing call emits headings as markdown, and the renderer parses them back:

```
## 1. EXECUTIVE SUMMARY      section heading
### Company Snapshot          subsection heading
- Round: common equity        bullet; "Round:" is set bold
Plain line                    body paragraph
```

Detection is deliberately tolerant, because models vary the surface form far
more than they vary the wording. All of these resolve to the same section:
`## 1. EXECUTIVE SUMMARY`, `EXECUTIVE SUMMARY`, `**EXECUTIVE SUMMARY**`,
`1. EXECUTIVE SUMMARY (ONE PAGE)`, and `WHAT DOESN'T` with a curly apostrophe.
An unrecognised heading is not dropped — it renders last, and the run prints a
note to stderr. A memo with no recognisable headings at all renders as one
untitled block rather than failing, since the API tokens are already spent.

### Section rendering

```
1. SECTION HEADING       SECTION_HEADER, numbered, ALL CAPS, keepWithNext
Subsection Heading       SUBSECTION_HEADER, title case, keepWithNext
Body paragraph.          BODY, full width, 2–4 lines
 •  Bullet line          BULLET, 12 pt indent, bullet at 5 pt
 •  Label: value         label set in Inter SemiBold
```

## 8. Closing line

`Prepared by TEN Capital`, CLOSING style, after the final section.

## 9. Footer — every page

```
TEN CAPITAL — CONFIDENTIAL                              PAGE X OF Y
```

- 0.5 pt `INK_300` hairline, 14 pt above the footer baseline, margin to margin
- Left string and right-aligned page number share the baseline
- FOOTER style, uppercase, 0.4 pt letter-spacing

## 10. Content rules

- Plain text only, beyond the `##` / `###` headings and `- ` bullets. No bold
  markup, no italics, no tables.
- No citations, footnotes, meta-commentary, or emoji.
- Facts in the structured data are the company's claims, not verified truth.
  Never invent a number, date, name, or citation that is not in the data.
- Where the deck gives no basis for a figure, say the figure is assumed rather
  than sourced.
- Where a section has no support in the data, state in one line what is missing
  and why it matters, rather than padding.
- Sections 12–15 are the analyst's view, not the deck's. Form a view and commit
  to it.
