"""Colour code of the alternate fingering names, and the legend drawn on the generated pages."""

from __future__ import annotations

from xml.sax.saxutils import escape

from windfingerflow.i18n import ui
from windfingerflow.models import Fingering, Level

TO_TEST = "to_test"
COLORS = {
    Level.BEGINNER.value: "#000000",
    Level.ADVANCED.value: "#2e7d32",
    Level.EXPERT.value: "#c62828",
    Level.EXPERIMENTAL.value: "#7b1fa2",
    TO_TEST: "#ef6c00",
}


def fingering_color(f: Fingering) -> str:
    """Orange while the saxophonist has not validated the fingering, otherwise by level."""
    return COLORS[TO_TEST] if not f.validated else COLORS[f.level.value]


def legend_svg(x: float, y: float, lang: str, size: float = 9) -> str:
    """One line of coloured labels starting at (x, y)."""
    t = ui(lang, "legend")
    out = [
        f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" fill="#444">{escape(t["title"])}</text>'
    ]
    cx = x + size * 0.52 * len(t["title"]) + 8
    for key in ("beginner", "advanced", "expert", "experimental", TO_TEST):
        out.append(
            f'<text x="{cx:g}" y="{y:g}" font-size="{size:g}" font-weight="bold" '
            f'fill="{COLORS[key]}">{escape(t[key])}</text>'
        )
        cx += size * 0.62 * len(t[key]) + 14
    return "\n".join(out)
