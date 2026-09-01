"""Resend email delivery: send each generated memo to the TEN Capital inbox.

Every successful generation — CLI or web — sends one email containing the memo
prose inline and the rendered PDF as an attachment. Sending is best-effort: a
failure here is reported but never fails a generation that already succeeded,
because the API tokens are spent and the PDF exists by that point.

Configuration (via .env or service variables):
    RESEND_API_KEY       required; without it notifications are skipped
    MEMO_EMAIL_TO        comma-separated recipients (default: Info@tencapital.group)
    MEMO_EMAIL_FROM      verified Resend sender (default: the resend.dev sandbox)
    MEMO_EMAIL_REPLY_TO  optional reply-to address
"""

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from html import escape

from dotenv import load_dotenv

load_dotenv()

RESEND_ENDPOINT = "https://api.resend.com/emails"
REQUEST_TIMEOUT_SECONDS = 30

DEFAULT_RECIPIENTS = "Info@tencapital.group"

# tencapital.group is verified for sending in Resend, so the default From uses
# it. Any override in MEMO_EMAIL_FROM must also be on a verified domain —
# Resend answers 403 otherwise.
DEFAULT_SENDER = "TEN Capital Memo Generator <memos@tencapital.group>"

# Resend sits behind Cloudflare, which blocks the default Python-urllib agent
# with "error code: 1010". Any identifiable agent string gets through.
USER_AGENT = "TENCapitalMemoGenerator/1.0"

# Brand colours, matching src/brand.py and the web UI.
_NAVY = "#101E33"
_CORAL = "#EE5A4E"
_AMBER = "#F3A22A"
_TEAL = "#35BEBB"
_INK = "#5C6E86"

# Structured-data fields surfaced in the email summary table, in order.
_SUMMARY_FIELDS = ["sector", "stage", "deal_stage", "proposed_investment",
                   "valuation"]


class EmailSendError(Exception):
    """Raised when Resend rejects the send or cannot be reached."""


def is_configured():
    """True when a Resend API key is present, so notifications can be sent."""
    return bool(os.getenv("RESEND_API_KEY"))


def recipients():
    """Recipient list, from MEMO_EMAIL_TO or the TEN Capital default."""
    raw = os.getenv("MEMO_EMAIL_TO") or DEFAULT_RECIPIENTS
    return [address.strip() for address in raw.split(",") if address.strip()]


def sender():
    """From address, from MEMO_EMAIL_FROM or the Resend sandbox default."""
    return os.getenv("MEMO_EMAIL_FROM") or DEFAULT_SENDER


def describe_target():
    """One-line summary of where notifications go, for status output."""
    if not is_configured():
        return "disabled (RESEND_API_KEY not set)"
    return f"{sender()} -> {', '.join(recipients())}"


def send_memo_email(
    pdf_bytes,
    pdf_filename,
    company_name,
    tagline,
    sections,
    structured_data=None,
    source_filename=None,
    origin="CLI",
):
    """Email one generated memo. Returns the Resend message id.

    Raises EmailSendError on any failure, including a missing API key —
    callers decide whether that is fatal (it is not, for a generation that
    already produced a PDF).
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise EmailSendError(
            "RESEND_API_KEY is not set. Add it to .env (or as a service "
            "variable) to enable memo notifications."
        )

    to = recipients()
    if not to:
        raise EmailSendError("MEMO_EMAIL_TO is set but contains no addresses.")

    company = (company_name or "Untitled company").strip()
    generated_at = datetime.now().astimezone().strftime("%d %b %Y, %H:%M %Z")

    payload = {
        "from": sender(),
        "to": to,
        "subject": f"Investment memo — {company}",
        "html": _html_body(
            company, tagline, sections, structured_data,
            source_filename, origin, generated_at,
            pdf_filename if pdf_bytes else None,
        ),
        "text": _text_body(
            company, tagline, sections, structured_data,
            source_filename, origin, generated_at,
            pdf_filename if pdf_bytes else None,
        ),
    }

    # tools/check_email.py sends without a PDF; Resend rejects empty content.
    if pdf_bytes:
        payload["attachments"] = [
            {
                "filename": pdf_filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ]

    reply_to = os.getenv("MEMO_EMAIL_REPLY_TO")
    if reply_to:
        payload["reply_to"] = reply_to

    return _post(api_key, payload)


def _post(api_key, payload):
    request = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            body = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        raise EmailSendError(
            f"Resend rejected the request (HTTP {exc.code}): "
            f"{_error_detail(exc)}"
        ) from exc
    except Exception as exc:
        raise EmailSendError(
            f"Could not reach Resend ({type(exc).__name__}): {exc}"
        ) from exc

    message_id = body.get("id")
    if not message_id:
        raise EmailSendError(f"Resend returned no message id: {body}")
    return message_id


def _error_detail(http_error):
    """Pull Resend's error message out of the response body, if there is one."""
    try:
        body = json.loads(http_error.read().decode("utf-8"))
    except Exception:
        return http_error.reason
    return body.get("message") or body.get("name") or str(body)


# --- Body rendering ----------------------------------------------------------

def _summary_rows(structured_data, source_filename, origin, generated_at):
    """Metadata rows for the summary table, skipping anything not present."""
    rows = [
        ("Generated", generated_at),
        ("Source", source_filename or "—"),
        ("Origin", origin),
    ]
    for key in _SUMMARY_FIELDS:
        value = (structured_data or {}).get(key)
        if value:
            rows.append((key.replace("_", " ").title(), str(value)))
    return rows


def _html_body(
    company, tagline, sections, structured_data,
    source_filename, origin, generated_at, pdf_filename,
):
    rows = "".join(
        f'<tr>'
        f'<td style="padding:6px 14px 6px 0;color:{_INK};font-size:12px;'
        f'text-transform:uppercase;letter-spacing:0.08em;white-space:nowrap;'
        f'vertical-align:top;">{escape(label)}</td>'
        f'<td style="padding:6px 0;color:{_NAVY};font-size:14px;'
        f'line-height:1.5;">{escape(value)}</td>'
        f'</tr>'
        for label, value in _summary_rows(
            structured_data, source_filename, origin, generated_at
        )
    )

    subtitle = (
        f'<div style="color:#C4D0E0;font-size:14px;margin-top:6px;'
        f'line-height:1.5;">{escape(tagline)}</div>'
        if tagline
        else ""
    )

    attachment_note = (
        f'The formatted one-pager is attached as '
        f'<b style="color:{_NAVY};">{escape(pdf_filename)}</b>. '
        f'The full memo text follows below.'
        if pdf_filename
        else "The full memo text follows below."
    )

    body = "".join(
        f'<h2 style="font-size:13px;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{_CORAL};margin:26px 0 8px;">'
        f'{escape(name or "MEMO")}</h2>'
        + "".join(
            f'<p style="margin:0 0 10px;color:{_NAVY};font-size:14px;'
            f'line-height:1.6;">{escape(paragraph.strip())}</p>'
            for paragraph in (text or "").split("\n\n")
            if paragraph.strip()
        )
        for name, text in sections
    )

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:24px;background:#F3F6FA;
             font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:640px;margin:0 auto;background:#FFFFFF;
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(11,21,38,0.08);">

    <div style="background:{_NAVY};padding:24px 28px;">
      <div style="color:{_TEAL};font-size:11px;letter-spacing:0.16em;
                  text-transform:uppercase;margin-bottom:8px;">
        TEN Capital Network &middot; Deck Analyzer
      </div>
      <div style="color:#FFFFFF;font-size:22px;font-weight:700;
                  line-height:1.3;">{escape(company)}</div>
      {subtitle}
    </div>
    <div style="height:3px;background:linear-gradient(90deg,{_CORAL},{_AMBER},{_TEAL});"></div>

    <div style="padding:24px 28px;">
      <table style="border-collapse:collapse;width:100%;">{rows}</table>

      <div style="margin-top:20px;padding:12px 14px;background:#F3F6FA;
                  border-radius:8px;color:{_INK};font-size:13px;
                  line-height:1.5;">{attachment_note}</div>

      <hr style="border:none;border-top:1px solid #E3E9F1;margin:24px 0 0;">
      {body}
    </div>

    <div style="padding:16px 28px 22px;border-top:1px solid #E3E9F1;
                color:{_INK};font-size:11px;line-height:1.5;">
      Compiled by TEN Capital Network. Generated automatically from an uploaded
      pitch deck — review before circulating.
    </div>
  </div>
</body>
</html>"""


def _text_body(
    company, tagline, sections, structured_data,
    source_filename, origin, generated_at, pdf_filename,
):
    lines = ["TEN CAPITAL — INVESTMENT MEMO", "", company]
    if tagline:
        lines.append(tagline)
    lines.append("")

    for label, value in _summary_rows(
        structured_data, source_filename, origin, generated_at
    ):
        lines.append(f"{label}: {value}")

    if pdf_filename:
        lines.extend(["", f"The formatted one-pager is attached ({pdf_filename})."])

    for name, text in sections:
        lines.extend(["", f"{name or 'MEMO'}:", (text or "").strip()])

    return "\n".join(lines)
