"""Fingering chart over the whole range: every note natural, flat, sharp and double sharp."""

from __future__ import annotations

from xml.sax.saxutils import escape

from windfingerflow.chooser import candidates, effective_keys
from windfingerflow.database import Database
from windfingerflow.fiati import FONT_FAMILY, diagram_text
from windfingerflow.instrument import WRITTEN_RANGE, midi_to_name
from windfingerflow.models import Category, Fingering
from windfingerflow.profile import Profile

PAGE_W, PAGE_H = 794, 1123  # A4 at 96 dpi
MARGIN = 40
CELL_W = 178
ROW_H = 140
ROWS_PER_PAGE = 7
HEADER_Y = 95
FIRST_ROW_Y = 115
DIAGRAM_SIZE = 100
MAX_DIAGRAMS = 4

LETTERS = ["C", "D", "E", "F", "G", "A", "B"]
BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SOLFEGE = {"C": "Do", "D": "Ré", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}
# (accidental label, semitone shift); double sharp is written with two sharps (font-safe).
ACCIDENTALS = [("", 0), ("♭", -1), ("♯", 1), ("♯♯", 2)]

TEXT = {
    "en": {
        "title": "Saxophone fingering chart (written pitch)",
        "cols": ["Natural", "Flat", "Sharp", "Double sharp"],
        "nodata": "no data",
        "note": "Palm keys and altissimo are not covered yet. Alternates are labelled under the chart.",
    },
    "fr": {
        "title": "Tableau de doigtés de saxophone (hauteur écrite)",
        "cols": ["Naturel", "Bémol", "Dièse", "Double dièse"],
        "nodata": "pas de données",
        "note": "Clés de paume et suraigu pas encore couverts. Les alternatives sont nommées sous le diagramme.",
    },
}


def note_label(letter: str, accidental: str, octave: int, naming: str) -> str:
    name = SOLFEGE[letter] if naming == "solfege" else letter
    return f"{name}{accidental}{octave}"


def chart_cells() -> list[tuple[str, int, list[tuple[str, int, int] | None]]]:
    """Rows of (letter, octave, cells) where each cell is (accidental, shift, midi) or None."""
    low, high = WRITTEN_RANGE
    rows = []
    for octave in range(3, 7):
        for letter in LETTERS:
            cells = []
            for accidental, shift in ACCIDENTALS:
                midi = (octave + 1) * 12 + BASE[letter] + shift
                cells.append((accidental, shift, midi) if low <= midi <= high else None)
            if any(cells):
                rows.append((letter, octave, cells))
    return rows


def _fingerings(db: Database, pitch: str, profile: Profile, alternates: bool) -> list[Fingering]:
    found = candidates(db, pitch, profile)
    found.sort(key=lambda f: (f.category != Category.STANDARD, f.id))
    if not alternates:
        found = [f for f in found if f.category == Category.STANDARD]
    return found[:MAX_DIAGRAMS]


def _cell(db, letter, octave, cell, col, row_y, profile, alternates, lang, naming) -> str:
    accidental, _shift, midi = cell
    x = MARGIN + col * CELL_W
    pitch = midi_to_name(midi)
    label = note_label(letter, accidental, octave, naming)
    out = [
        f'<text x="{x + 6}" y="{row_y + 14}" font-size="14" font-weight="bold">{escape(label)}</text>'
    ]
    found = _fingerings(db, pitch, profile, alternates)
    if not found:
        out.append(
            f'<text x="{x + 6}" y="{row_y + 60}" font-size="10" fill="#888">{escape(TEXT[lang]["nodata"])}</text>'
        )
        return "\n".join(out)
    base_y = row_y + 22 + DIAGRAM_SIZE
    for i, f in enumerate(found):
        dx = x + 6 + i * 42
        glyphs = escape(diagram_text(effective_keys(f, pitch)))
        out.append(
            f'<text x="{dx}" y="{base_y}" font-family="{FONT_FAMILY}" font-size="{DIAGRAM_SIZE}">{glyphs}</text>'
        )
        if f.category != Category.STANDARD:
            name = getattr(f.name, lang, None) or f.name.en
            out.append(
                f'<text x="{dx}" y="{base_y + 11}" font-size="7.5">{escape(name[:11])}</text>'
            )
    return "\n".join(out)


def chart_svg_pages(
    db: Database,
    profile: Profile | None = None,
    *,
    alternates: bool = False,
    lang: str = "en",
    naming: str = "letters",
    responsive: bool = False,
) -> list[str]:
    """SVG pages. ``responsive`` drops the fixed size and loads Fiati via @font-face (web preview)."""
    profile = profile or Profile()
    t = TEXT[lang]
    rows = chart_cells()
    pages = []
    for start in range(0, len(rows), ROWS_PER_PAGE):
        body = [
            f'<text x="{MARGIN}" y="55" font-size="24" font-weight="bold">{escape(t["title"])}</text>'
        ]
        for col, name in enumerate(t["cols"]):
            body.append(
                f'<text x="{MARGIN + col * CELL_W + 6}" y="{HEADER_Y}" font-size="13" fill="#555">{escape(name)}</text>'
            )
        for r, (letter, octave, cells) in enumerate(rows[start : start + ROWS_PER_PAGE]):
            row_y = FIRST_ROW_Y + r * ROW_H
            body.append(
                f'<line x1="{MARGIN}" y1="{row_y - 4}" x2="{PAGE_W - MARGIN}" y2="{row_y - 4}" stroke="#ccc"/>'
            )
            for col, cell in enumerate(cells):
                if cell:
                    body.append(
                        _cell(
                            db, letter, octave, cell, col, row_y, profile, alternates, lang, naming
                        )
                    )
        body.append(
            f'<text x="{MARGIN}" y="{PAGE_H - 30}" font-size="9" fill="#666">{escape(t["note"])}</text>'
        )
        size = "" if responsive else f' width="{PAGE_W}" height="{PAGE_H}"'
        style = (
            "<style>@font-face{font-family:Fiati;src:url(/fonts/fiati-regular.ttf)}svg{background:#fff}</style>"
            if responsive
            else ""
        )
        pages.append(
            f'<svg xmlns="http://www.w3.org/2000/svg"{size} viewBox="0 0 {PAGE_W} {PAGE_H}" '
            f'font-family="DejaVu Sans, sans-serif">{style}<rect width="100%" height="100%" fill="white"/>'
            + "\n".join(body)
            + "</svg>"
        )
    return pages
