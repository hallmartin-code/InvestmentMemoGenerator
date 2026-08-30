"""CLI entry point: pitch deck (PDF/PPTX) -> one-page TEN Capital memo PDF."""

import argparse
import sys
from pathlib import Path

import extractor
import layout
import notifier
import parser as deck_parser
import template
import writer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def build_arg_parser():
    ap = argparse.ArgumentParser(
        prog="main.py",
        description="Generate a one-page TEN Capital investment memo from a pitch deck.",
    )
    ap.add_argument(
        "--input",
        required=True,
        help="Path to the pitch deck (.pdf or .pptx)",
    )
    ap.add_argument(
        "--output",
        help="Path for the generated memo PDF "
             "(default: output/<input_stem>_memo.pdf)",
    )
    ap.add_argument(
        "--no-email",
        action="store_true",
        help="Skip the Resend notification that is otherwise sent to "
             f"{notifier.DEFAULT_RECIPIENTS} on success",
    )
    return ap


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def main(argv=None):
    args = build_arg_parser().parse_args(argv)

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        fail(f"Input file not found: {input_path}")

    if input_path.suffix.lower() not in deck_parser.SUPPORTED_EXTENSIONS:
        fail(
            f"Unsupported file type '{input_path.suffix}'. "
            f"Supported formats: {', '.join(deck_parser.SUPPORTED_EXTENSIONS)}"
        )

    output_path = (
        Path(args.output).expanduser()
        if args.output
        else DEFAULT_OUTPUT_DIR / f"{input_path.stem}_memo.pdf"
    )

    # Fail on missing fonts before spending money on API calls.
    try:
        layout.register_fonts()
    except layout.FontsNotFoundError as exc:
        fail(str(exc))

    print(f"Parsing {input_path.name} ...")
    try:
        raw_text = deck_parser.parse_deck(input_path)
    except deck_parser.DeckParseError as exc:
        fail(str(exc))

    print("Extracting structured data ...")
    try:
        data = extractor.extract_structured_data(raw_text)
    except extractor.MalformedJSONError as exc:
        print("Error: the extraction response was not valid JSON.", file=sys.stderr)
        print("--- raw API response ---", file=sys.stderr)
        print(exc.raw_response, file=sys.stderr)
        print("--- end raw API response ---", file=sys.stderr)
        sys.exit(1)
    except extractor.APICallError as exc:
        fail(str(exc))

    # Guarantee every template field exists, even if the model omitted keys.
    data = {**template.blank_structured_data(), **data}

    print("Writing memo ...")
    try:
        memo_text = extractor.write_memo(data)
    except extractor.APICallError as exc:
        fail(str(exc))

    sections, degraded = writer.sections_or_fallback(memo_text)
    if not sections:
        fail(
            "The memo response was empty, so there is nothing to render.\n"
            "--- raw memo text ---\n" + memo_text
        )
    if degraded:
        print(
            "Note: no section headers were found in the memo, so it is being "
            "rendered as a single block.",
            file=sys.stderr,
        )

    unexpected = template.unknown_section_names(sections)
    if unexpected:
        print(
            "Note: section(s) outside the template will render last: "
            + ", ".join(unexpected),
            file=sys.stderr,
        )
    sections = template.order_sections(sections)

    header_title = data.get(template.HEADER_FIELDS["title"]) or ""
    header_subtitle = data.get(template.HEADER_FIELDS["subtitle"]) or ""

    try:
        written = writer.build_pdf(
            output_path,
            company_name=header_title,
            tagline=header_subtitle,
            sections=sections,
        )
    except layout.FontsNotFoundError as exc:
        fail(str(exc))
    except Exception as exc:
        fail(f"PDF rendering failed ({type(exc).__name__}): {exc}")

    print(f"Memo written to {written}")

    # Best-effort: the PDF exists and the tokens are spent, so a failed
    # notification is reported but never changes the exit code.
    if args.no_email:
        print("Email notification skipped (--no-email).")
    elif not notifier.is_configured():
        print(
            "Note: no email sent — RESEND_API_KEY is not set.",
            file=sys.stderr,
        )
    else:
        try:
            message_id = notifier.send_memo_email(
                pdf_bytes=Path(written).read_bytes(),
                pdf_filename=Path(written).name,
                company_name=header_title,
                tagline=header_subtitle,
                sections=sections,
                structured_data=data,
                source_filename=input_path.name,
                origin="CLI",
            )
            print(
                f"Emailed to {', '.join(notifier.recipients())} "
                f"(id {message_id})"
            )
        except notifier.EmailSendError as exc:
            print(f"Note: memo email not sent — {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
