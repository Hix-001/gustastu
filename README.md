# Love You

A small generative typographic piece: a heart made of *I love you* in many languages, drawn with Python’s standard library.

## Run

```bash
python love.py
```

No packages to install. Needs a desktop Python with Tk (the usual `python.org` and Windows installs include it).

## While it plays

| Key | Action |
| --- | --- |
| click or space | play again (same layout) |
| r | new random heart |
| esc | close |

Phrases pick a system font that can actually draw that script (Hangul, CJK, Devanagari, Thai, Arabic, Hebrew, Cyrillic), so the silhouette stays readable instead of falling back to boxes.

Spawn follows a heartbeat cadence. After the last word lands, the type breathes and occasional phrases glimmer.

## How the shape is built

The classic parametric heart curve is scan-converted into rows. Each row is packed with shuffled phrases until the chord is full, then the line is gently justified so the silhouette stays dense at the edges. Rim words draw first, then the interior fills inward.
