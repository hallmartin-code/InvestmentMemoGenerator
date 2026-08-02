# Fonts

The TEN Capital brand typefaces — Sora (headings), Inter (body), JetBrains Mono
(metadata). They are **not** bundled with this repo.

## Fetch them automatically

```
pip install fonttools
python tools/fetch_brand_fonts.py
```

## Or download by hand

| File | Family | Source |
| --- | --- | --- |
| `Sora-Bold.ttf` | Sora 700 | https://fonts.google.com/specimen/Sora |
| `Sora-SemiBold.ttf` | Sora 600 | https://fonts.google.com/specimen/Sora |
| `Inter-Regular.ttf` | Inter 400 | https://fonts.google.com/specimen/Inter |
| `JetBrainsMono-Medium.ttf` | JetBrains Mono 500 | https://fonts.google.com/specimen/JetBrains+Mono |

Sora and Inter download from Google Fonts as **variable** fonts
(`Sora[wght].ttf`, `Inter[opsz,wght].ttf`), which ReportLab cannot read. Use the
files from each archive's `static/` folder, renamed to match the table above —
or just run the fetch script, which instances them for you.
