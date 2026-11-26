"""Fingering diagrams as text, using the Fiati font (SIL OFL 1.1).

A diagram is the blank saxophone chart glyph followed by one zero-width overlay glyph per
pressed key. Codepoints come from Fiati's glyph metadata (``glyph-metadata.ods``).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from xml.sax.saxutils import escape

FONT_FAMILY = "Fiati"
FONTS_DIR = Path(__file__).resolve().parents[2] / "fonts"

# Verovio ignores the font size of <words>; diagrams are enlarged by this factor when the
# SVG is post-processed (a chart is drawn small at the normal text size).
DIAGRAM_SCALE = 2.4

SAX_CHART = 0xE280
SAX_BARITONE_LOW_A_OPEN = 0xE281

# Our key id -> Fiati "closed" overlay glyph.
KEY_GLYPHS: dict[str, int] = {
    "lh.octave": 0xE282,
    "lh.front_f": 0xE283,
    "lh.b": 0xE284,  # LH 1st finger
    "lh.bis": 0xE285,
    "lh.a": 0xE286,  # LH 2nd finger
    "lh.g": 0xE287,  # LH 3rd finger
    "lh.palm_eb": 0xE288,
    "lh.palm_d": 0xE289,
    "lh.palm_f": 0xE28A,
    "lh.gs": 0xE28B,
    "lh.low_cs": 0xE28C,
    "lh.low_b": 0xE28D,
    "lh.low_bb": 0xE28E,
    "rh.side_e": 0xE28F,
    "rh.side_c": 0xE290,
    "rh.side_bb": 0xE291,
    "rh.high_fs": 0xE292,
    "rh.f": 0xE293,  # RH 1st finger
    "rh.e": 0xE294,  # RH 2nd finger
    "rh.alt_fs": 0xE295,
    "rh.d": 0xE296,  # RH 3rd finger
    "rh.low_eb": 0xE297,
    "rh.low_c": 0xE298,
    "lh.low_a": 0xE299,
}


def diagram_text(keys: Iterable[str]) -> str:
    """Text to set in the Fiati font to draw a chart with these keys pressed."""
    missing = [k for k in keys if k not in KEY_GLYPHS]
    if missing:
        raise KeyError(f"no Fiati glyph for keys: {missing}")
    return chr(SAX_CHART) + "".join(chr(KEY_GLYPHS[k]) for k in sorted(keys, key=KEY_GLYPHS.get))


PRESSED_COLOR = "#d81b60"  # pressed keys stand out from the black outline of the instrument


def diagram_markup(keys: Iterable[str], color: str = PRESSED_COLOR) -> str:
    """SVG text content of a diagram: black outline, pressed keys in colour (same text flow)."""
    text = diagram_text(keys)
    return (
        f'<tspan fill="#000">{escape(text[0])}</tspan>'
        f'<tspan fill="{color}">{escape(text[1:])}</tspan>'
    )
