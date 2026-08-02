"""Flask front end: upload a deck, get the one-pager PDF back.

Wraps the same pipeline the CLI uses (parser -> extractor -> writer). Run
locally with `python web/app.py`; in production gunicorn serves `app:app`.
"""

import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

import extractor
import layout
import parser as deck_parser
import template
import writer

MAX_UPLOAD_MB = 25

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def _fonts_ready():
    return all(
        (layout.FONTS_DIR / filename).is_file()
        for filename in layout.FONT_FILES.values()
    )


@app.get("/")
def index():
    return render_template(
        "index.html",
        accepted=",".join(deck_parser.SUPPORTED_EXTENSIONS),
        max_mb=MAX_UPLOAD_MB,
    )


@app.get("/healthz")
def healthz():
    """Readiness probe — reports config without spending tokens."""
    return jsonify(
        ok=bool(os.getenv("ANTHROPIC_API_KEY")) and _fonts_ready(),
        api_key_configured=bool(os.getenv("ANTHROPIC_API_KEY")),
        fonts_ready=_fonts_ready(),
        model=extractor.MODEL,
        accepted=list(deck_parser.SUPPORTED_EXTENSIONS),
    )


@app.post("/generate")
def generate():
    upload = request.files.get("deck")
    if upload is None or not upload.filename:
        return jsonify(error="No file was uploaded."), 400

    filename = secure_filename(upload.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in deck_parser.SUPPORTED_EXTENSIONS:
        return jsonify(
            error=f"Unsupported file type '{suffix}'. Supported formats: "
                  + ", ".join(deck_parser.SUPPORTED_EXTENSIONS)
        ), 400

    if not _fonts_ready():
        return jsonify(
            error="Brand fonts are not installed on the server. Run "
                  "tools/fetch_brand_fonts.py during the build."
        ), 500

    with tempfile.TemporaryDirectory() as workdir:
        source = Path(workdir) / filename
        upload.save(source)

        try:
            raw_text = deck_parser.parse_deck(source)
        except deck_parser.DeckParseError as exc:
            return jsonify(error=str(exc)), 400

        try:
            data = extractor.extract_structured_data(raw_text)
        except extractor.MalformedJSONError:
            return jsonify(
                error="Claude returned malformed JSON during extraction. "
                      "Try again — if it persists the deck may be unusually "
                      "structured."
            ), 502
        except extractor.APICallError as exc:
            return jsonify(error=str(exc)), 502

        data = {**template.blank_structured_data(), **data}

        try:
            memo_text = extractor.write_memo(data)
        except extractor.APICallError as exc:
            return jsonify(error=str(exc)), 502

        sections = writer.parse_memo_sections(memo_text)
        if not sections:
            return jsonify(
                error="Claude's memo had no section headers, so there was "
                      "nothing to render."
            ), 502
        sections = template.order_sections(sections)

        output = Path(workdir) / f"{Path(filename).stem}_memo.pdf"
        try:
            writer.build_pdf(
                output,
                company_name=data.get(template.HEADER_FIELDS["title"]) or "",
                tagline=data.get(template.HEADER_FIELDS["subtitle"]) or "",
                sections=sections,
            )
        except layout.FontsNotFoundError as exc:
            return jsonify(error=str(exc)), 500
        except Exception as exc:
            return jsonify(
                error=f"PDF rendering failed ({type(exc).__name__}): {exc}"
            ), 500

        # Read before the temp dir is removed.
        pdf_bytes = output.read_bytes()
        download_name = output.name

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exc):
    return jsonify(error=f"File is larger than {MAX_UPLOAD_MB} MB."), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=bool(os.getenv("FLASK_DEBUG")),
    )
