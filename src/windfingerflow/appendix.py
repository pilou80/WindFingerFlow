"""Detailed appendix pages: one large diagram per alternate fingering used, with its bars."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from windfingerflow.chooser import effective_keys
from windfingerflow.fiati import FONT_FAMILY, diagram_text
from windfingerflow.models import Category, Fingering
from windfingerflow.score import NoteEvent

PAGE_W, PAGE_H = 794, 1123  # A4 at 96 dpi
BLOCK_H = 300
BLOCKS_PER_PAGE = 3
MARGIN = 60
DIAGRAM_SIZE = 120

LABELS = {
    "en": {
        "title": "Alternate fingerings used",
        "bars": "Bars",
        "level": "Level",
        "intonation": "Intonation",
        "use": "Use",
        "avoid": "Avoid",
        "unconfirmed": "Awaiting verification",
        "sharp": "tends to be sharp",
        "flat": "tends to be flat",
        "in_tune": "in tune",
        "reference": "reference",
        "beginner": "beginner",
        "advanced": "advanced",
        "expert": "expert",
        "experimental": "experimental",
    },
    "fr": {
        "title": "Doigtés alternatifs utilisés",
        "bars": "Mesures",
        "level": "Niveau",
        "intonation": "Intonation",
        "use": "Usage",
        "avoid": "À éviter",
        "unconfirmed": "En attente de vérification",
        "sharp": "tend à être haut",
        "flat": "tend à être bas",
        "in_tune": "juste",
        "reference": "référence",
        "beginner": "débutant",
        "advanced": "avancé",
        "expert": "expert",
        "experimental": "expérimental",
    },
}


@dataclass
class Entry:
    fingering: Fingering
    pitch: str  # first pitch it was used on (sets the register shown in the diagram)
    bars: list[int] = field(default_factory=list)


def collect_entries(events: list[NoteEvent], chosen: list[Fingering | None]) -> list[Entry]:
    """Alternate (non-standard) fingerings actually used, in order of first use."""
    entries: dict[str, Entry] = {}
    for event, fingering in zip(events, chosen, strict=True):
        if fingering is None or fingering.category == Category.STANDARD:
            continue
        entry = entries.setdefault(fingering.id, Entry(fingering, event.pitch))
        if event.measure is not None and event.measure not in entry.bars:
            entry.bars.append(event.measure)
    for entry in entries.values():
        entry.bars.sort()
    return list(entries.values())


def format_bars(bars: list[int]) -> str:
    """[3, 4, 5, 8] -> '3-5, 8'."""
    if not bars:
        return "-"
    runs: list[list[int]] = [[bars[0], bars[0]]]
    for bar in bars[1:]:
        if bar == runs[-1][1] + 1:
            runs[-1][1] = bar
        else:
            runs.append([bar, bar])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


def _lines(text: str, width: int = 52) -> list[str]:
    return textwrap.wrap(text, width) if text else []


def _block(entry: Entry, top: int, lang: str) -> str:
    t = LABELS[lang]
    f = entry.fingering
    name = getattr(f.name, lang, None) or f.name.en
    glyphs = escape(diagram_text(effective_keys(f, entry.pitch)))
    x_text = MARGIN + 200
    out = [
        (
            f'<text x="{MARGIN}" y="{top + 230}" font-family="{FONT_FAMILY}" '
            f'font-size="{DIAGRAM_SIZE * 2}">{glyphs}</text>'
        ),
        f'<text x="{x_text}" y="{top + 40}" font-size="26" font-weight="bold">{escape(name)}</text>',
    ]
    meta = [f"{t['level']}: {t[f.level.value]}"]
    if f.intonation.value != "unknown":
        extra = f" ({f.cents:+g} cents)" if f.cents is not None else ""
        meta.append(f"{t['intonation']}: {t[f.intonation.value]}{extra}")
    lines = [" - ".join(meta)]
    if f.use:
        lines += _lines(f"{t['use']}: {f.use}")
    if f.avoid:
        lines += _lines(f"{t['avoid']}: {f.avoid}")
    lines += _lines(f"{t['bars']}: {format_bars(entry.bars)}")
    if f.needs_confirmation:
        lines.append(f"! {t['unconfirmed']}")
    y = top + 75
    for line in lines:
        out.append(f'<text x="{x_text}" y="{y}" font-size="15">{escape(line)}</text>')
        y += 22
    out.append(
        f'<line x1="{MARGIN}" y1="{top + BLOCK_H - 20}" x2="{PAGE_W - MARGIN}" '
        f'y2="{top + BLOCK_H - 20}" stroke="#bbb"/>'
    )
    return "\n".join(out)


def appendix_svg_pages(entries: list[Entry], lang: str = "en") -> list[str]:
    pages = []
    for start in range(0, len(entries), BLOCKS_PER_PAGE):
        body = [
            (
                f'<text x="{MARGIN}" y="70" font-size="30" font-weight="bold">'
                f"{escape(LABELS[lang]['title'])}</text>"
            )
        ]
        for i, entry in enumerate(entries[start : start + BLOCKS_PER_PAGE]):
            body.append(_block(entry, 110 + i * BLOCK_H, lang))
        pages.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" '
            f'viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="DejaVu Sans, sans-serif">'
            f'<rect width="100%" height="100%" fill="white"/>' + "\n".join(body) + "</svg>"
        )
    return pages
