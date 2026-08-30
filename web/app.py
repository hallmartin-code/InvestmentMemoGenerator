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

from flask import (
    Flask, jsonify, render_template, request, send_file, send_from_directory,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

import extractor
import layout
import notifier
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
        email_to=", ".join(notifier.recipients()) if notifier.is_configured() else "",
    )


@app.get("/favicon.ico")
def favicon():
    """Browsers request /favicon.ico at the root regardless of the link tags."""
    return send_from_directory(
        app.static_folder, "favicon.ico", mimetype="image/x-icon"
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
        email_configured=notifier.is_configured(),
        email_to=notifier.recipients(),
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

        sections, degraded = writer.sections_or_fallback(memo_text)
        if not sections:
            return jsonify(
                error="Claude returned an empty memo. Try again — if it "
                      "persists, the deck may have too little usable text."
            ), 502
        if degraded:
            app.logger.warning(
                "No section headers found; rendering memo as a single block."
            )
        else:
            sections = template.order_sections(sections)

        company_name = data.get(template.HEADER_FIELDS["title"]) or ""
        tagline = data.get(template.HEADER_FIELDS["subtitle"]) or ""

        output = Path(workdir) / f"{Path(filename).stem}_memo.pdf"
        try:
            writer.build_pdf(
                output,
                company_name=company_name,
                tagline=tagline,
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

    # Best-effort: the memo is already rendered, so a notification failure is
    # logged and reported in a header rather than failing the download.
    email_status = _notify(
        pdf_bytes, download_name, company_name, tagline, sections, data, filename
    )

    response = send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )
    response.headers["X-Memo-Email"] = email_status
    return response


def _notify(pdf_bytes, download_name, company_name, tagline, sections, data,
            source_filename):
    """Send the memo email. Returns a short status string for the client."""
    if not notifier.is_configured():
        app.logger.warning("RESEND_API_KEY not set; memo email skipped.")
        return "skipped: RESEND_API_KEY not set"

    try:
        notifier.send_memo_email(
            pdf_bytes=pdf_bytes,
            pdf_filename=download_name,
            company_name=company_name,
            tagline=tagline,
            sections=sections,
            structured_data=data,
            source_filename=source_filename,
            origin="Web app",
        )
    except notifier.EmailSendError as exc:
        app.logger.error("Memo email failed: %s", exc)
        return _header_safe(f"failed: {exc}")

    recipients = ", ".join(notifier.recipients())
    app.logger.info("Memo emailed to %s", recipients)
    return _header_safe(f"sent: {recipients}")


def _header_safe(text):
    """HTTP headers are latin-1; upstream error text may not be."""
    return text.encode("ascii", "replace").decode("ascii")


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exc):
    return jsonify(error=f"File is larger than {MAX_UPLOAD_MB} MB."), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=bool(os.getenv("FLASK_DEBUG")),
    )
