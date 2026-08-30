"""Verify the Resend configuration before relying on memo notifications.

Sends one small test email — no PDF attachment, no Claude tokens — and reports
what came back.

Run: python tools/check_email.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import notifier  # loads .env via python-dotenv


SAMPLE_SECTIONS = [
    (
        "EXECUTIVE SUMMARY",
        "This is a test message from the TEN Capital memo generator. If it "
        "arrived, generated memos will be delivered to this inbox "
        "automatically.",
    ),
    (
        "FINAL INVESTOR TAKE",
        "No action needed — this deal does not exist.",
    ),
]


def main():
    if not notifier.is_configured():
        print(
            "RESEND_API_KEY is not set.\n\n"
            "  1. Create a key at https://resend.com/api-keys\n"
            "  2. Copy .env.example to .env\n"
            "  3. Put the key in .env as RESEND_API_KEY=re_...\n\n"
            "On Railway, set it as a service variable instead of using .env.",
            file=sys.stderr,
        )
        return 1

    print(f"From:  {notifier.sender()}")
    print(f"To:    {', '.join(notifier.recipients())}")
    print("Sending a test email ...")

    try:
        message_id = notifier.send_memo_email(
            pdf_bytes=b"",
            pdf_filename="test_memo.pdf",
            company_name="Test Company",
            tagline="A configuration check, not a real deal.",
            sections=SAMPLE_SECTIONS,
            structured_data={"stage": "n/a", "ask": "n/a"},
            source_filename="check_email.py",
            origin="Configuration check",
        )
    except notifier.EmailSendError as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        print(
            "\nCommon causes:\n"
            "  401 / restricted    -> key is wrong, revoked, or read-only\n"
            "  403 domain          -> MEMO_EMAIL_FROM is not on a verified\n"
            "                         domain; verify it at resend.com/domains\n"
            "  422 validation      -> the sandbox sender onboarding@resend.dev\n"
            "                         only delivers to the account owner",
            file=sys.stderr,
        )
        return 1

    print(f"\nOK — Resend accepted the message (id {message_id}).")
    print("Check the inbox; delivery can lag a few seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
