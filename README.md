# TEN Capital — Pitch Deck to One-Pager Generator

Takes an investor pitch deck (PDF or PPTX) and produces a formatted one-page
investment memo PDF in TEN Capital house style.

## Setup

```
pip install -r requirements.txt
cp .env.example .env               # then add your ANTHROPIC_API_KEY
python tools/fetch_brand_fonts.py  # Sora, Inter, JetBrains Mono
```

The brand fonts are not bundled. The fetch script pulls them from Google Fonts
and instances the static weights; see [fonts/README.md](fonts/README.md) for the
manual route.

Get an API key from [console.anthropic.com](https://console.anthropic.com/settings/keys),
put it in `.env`, then confirm it works before running a real deck:

```
python tools/check_api.py
```

That sends one ~16-token request and reports the key, the model, and the reply.

## Usage

### CLI

```
python src/main.py --input path/to/deck.pdf --output output/memo.pdf
python src/main.py --input path/to/deck.pptx
```

With `--output` omitted, the memo lands at `output/<input_stem>_memo.pdf`.
Accepted inputs: `.pdf`, `.pptx`, `.docx`.

### Web app

```
python web/app.py          # http://localhost:5000
```

Upload a deck, get the PDF back as a download. `GET /healthz` reports whether
the API key and brand fonts are in place.

## Deploying to Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**, pick the repo.
3. Add one service variable: `ANTHROPIC_API_KEY` = your console key.
   Optionally `ANTHROPIC_MODEL` to override the pinned model.
4. Deploy. Railway reads [`railway.json`](railway.json) for the build and start
   commands and health check.

[`railway.json`](railway.json) fetches the brand fonts during the build, so
nothing font-related needs committing — `fonts/*.ttf` stays gitignored.

Notes:

- **Timeouts.** Two Claude calls run per request, typically 30–90s. gunicorn is
  configured with `--timeout 300`; don't lower it.
- **Concurrency.** `--workers 2 --threads 4` handles light traffic. Each request
  holds a worker thread for the whole generation, so raise workers before
  sharing the URL widely.
- **State.** Uploads go to a temp directory that is deleted when the request
  ends. Nothing persists on the server.
- **Cost.** Every upload spends tokens on two Opus calls. The URL is public
  unless you put auth in front of it.

## How it works

| Step | Module | What happens |
| --- | --- | --- |
| 1 | `parser.py` | pdfplumber (PDF), python-pptx (PPTX), or python-docx (DOCX) → one raw text string, slide boundaries marked |
| 2 | `extractor.py` | Claude call #1 → structured JSON (company, problem, traction, ask, risks, …) |
| 3 | `extractor.py` | Claude call #2 → memo prose with ALL-CAPS section headers |
| 4 | `writer.py` | ReportLab Platypus → US Letter PDF, 1in margins, brand masthead, footer on every page |

## Branding

[`src/brand.py`](src/brand.py) holds the TEN Capital Network brand system,
transcribed from the Deck Analyzer reference page: the navy/coral/amber/teal
palette, the Sora + Inter + JetBrains Mono pairing, and the tri-figure logo mark
drawn as vectors.

The reference is a dark UI. Reversing a full navy page for print would be
unreadable and toner-heavy, so the memo runs navy ink on white and asserts the
brand through three elements: a full-bleed navy masthead with the mark and
wordmark, the coral → amber → teal accent rule beneath it, and the typeface
pairing throughout.

## Document structure

[`src/template.py`](src/template.py) is the single source of truth for what a
memo contains — the 12 extraction fields and the 7 memo sections. Both Claude
prompts and the renderer are generated from it, so changing the document
structure means editing that one file. Adding a section there adds it to the
writing prompt and to the render order; adding an extraction field adds it to
the extraction schema.

[`templates/memo_structure.md`](templates/memo_structure.md) is the written
counterpart: page setup, type scale, header block, field definitions, section
purposes, and footer spec, with no company content.

Sections are rendered in template order regardless of the order the model
returns them. A header outside the template is not dropped — it renders last
and the run prints a note to stderr.

The model is pinned to `claude-opus-4-5`. Override it with `ANTHROPIC_MODEL` in
`.env` (e.g. `claude-opus-5`) without touching code.

## Test fixtures

`tests/make_sample_deck.py` generates a synthetic deck in both formats:

```
python tests/make_sample_deck.py
python src/main.py --input tests/sample_deck.pdf
```

## Exit codes

`1` on: input file missing, unsupported extension, unreadable or text-free deck,
brand fonts not installed, API call failure, or malformed extraction JSON (the raw
API response is printed to stderr in that case).

The web app maps the same failures to HTTP: `400` bad upload or unreadable deck,
`413` over 25 MB, `500` server-side (fonts, rendering), `502` upstream Claude
failure. Errors come back as `{"error": "..."}` and surface in the UI.
