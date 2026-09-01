"""Fetch the TEN Capital brand fonts into fonts/.

Sora and Inter ship from Google Fonts as variable fonts, which ReportLab cannot
read. This script downloads them and instances the static weights the memo
needs. JetBrains Mono is already static upstream.

Requires fonttools:  pip install fonttools

Run: python tools/fetch_brand_fonts.py

Alternative: download each family from fonts.google.com and copy the files from
the archive's static/ folder, renamed to match the targets below.
"""

import io
import sys
import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/main/ofl"
JETBRAINS = (
    "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/ttf"
)

# Variable sources -> static instances to generate.
#   url, [(axis pins, output filename), ...]
VARIABLE_SOURCES = [
    (
        f"{GOOGLE_FONTS}/sora/Sora%5Bwght%5D.ttf",
        [
            ({"wght": 700}, "Sora-Bold.ttf"),
            ({"wght": 600}, "Sora-SemiBold.ttf"),
        ],
    ),
    (
        f"{GOOGLE_FONTS}/inter/Inter%5Bopsz,wght%5D.ttf",
        [
            ({"opsz": 14, "wght": 400}, "Inter-Regular.ttf"),
            # Bold labels inside body text ("Round: common equity").
            ({"opsz": 14, "wght": 600}, "Inter-SemiBold.ttf"),
        ],
    ),
]

# Already static upstream.
STATIC_SOURCES = [
    (f"{JETBRAINS}/JetBrainsMono-Medium.ttf", "JetBrainsMono-Medium.ttf"),
]


def download(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main():
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        print(
            "fonttools is required to instance the variable fonts.\n"
            "  pip install fonttools\n"
            "Or download the families from fonts.google.com and copy the "
            "static/ files into fonts/ by hand.",
            file=sys.stderr,
        )
        return 1

    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    for url, instances in VARIABLE_SOURCES:
        print(f"Downloading {url.rsplit('/', 1)[-1]} ...")
        data = download(url)
        for axes, filename in instances:
            font = TTFont(io.BytesIO(data))
            # updateFontNames rewrites the name table from STAT, so the static
            # files identify as Sora-Bold / Inter-Regular rather than all
            # inheriting the variable font's default name.
            static = instancer.instantiateVariableFont(
                font, axes, inplace=True, updateFontNames=True
            )
            target = FONTS_DIR / filename
            static.save(str(target))
            pins = ", ".join(f"{k}={v}" for k, v in axes.items())
            print(f"  wrote {filename}  ({pins})")

    for url, filename in STATIC_SOURCES:
        print(f"Downloading {filename} ...")
        (FONTS_DIR / filename).write_bytes(download(url))
        print(f"  wrote {filename}")

    print(f"\nBrand fonts ready in {FONTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
