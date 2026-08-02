"""Verify the Anthropic API key and model before running a real deck.

Sends one tiny request (a few tokens) and reports what came back.

Run: python tools/check_api.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import extractor  # loads .env via python-dotenv


def main():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print(
            "ANTHROPIC_API_KEY is not set.\n\n"
            "  1. Create a key at https://console.anthropic.com/settings/keys\n"
            "  2. Copy .env.example to .env\n"
            "  3. Put the key in .env as ANTHROPIC_API_KEY=sk-ant-...\n\n"
            "On Railway, set it as a service variable instead of using .env.",
            file=sys.stderr,
        )
        return 1

    print(f"Key:   {key[:11]}...{key[-4:]}  ({len(key)} chars)")
    print(f"Model: {extractor.MODEL}")
    print("Sending a test request ...")

    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=extractor.MODEL,
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the word: ready"}],
        )
    except Exception as exc:
        print(f"\nFAILED ({type(exc).__name__}): {exc}", file=sys.stderr)
        print(
            "\nCommon causes:\n"
            "  401 authentication_error  -> key is wrong or revoked\n"
            "  404 not_found_error       -> model id not available to this key\n"
            "  400 invalid_request_error -> check ANTHROPIC_MODEL in .env\n"
            "  credit balance too low    -> add credits in the console",
            file=sys.stderr,
        )
        return 1

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    print(f"\nOK — model replied: {text!r}")
    print(
        f"Tokens: in={response.usage.input_tokens} "
        f"out={response.usage.output_tokens}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
