"""Fingering chart over the whole range: every note on a staff, natural, flat, sharp, double sharp."""

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
HEADER_Y = 95
FIRST_ROW_Y = 112
BOTTOM_MARGIN = 50
DIAGRAM_SIZE = 100
DIAGRAM_STEP = 42
MAX_DIAGRAMS = 4

# Staff geometry. Positions are diatonic steps: octave * 7 + letter index (C=0 ... B=6),
# so E4, the bottom line of the treble staff, is 30.
STAFF_SPACE = 6
STEP = STAFF_SPACE / 2
STAFF_W = 92
NOTE_X = 54
LINE_POSITIONS = (30, 32, 34, 36, 38)
G_LINE = 32
MUSIC_FONT = "Bravura"
MUSIC_FONT_SIZE = 4 * STAFF_SPACE  # SMuFL: a font size of four staff spaces
CLEF_G = "\ue050"
NOTEHEAD_WHOLE = "\ue0a2"
ACCIDENTAL_GLYPH = {"": "", "♭": "\ue260", "♯": "\ue262", "♯♯": "\ue263"}

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
        "note": "Palm keys and altissimo are not covered yet. Alternates are named under the diagram.",
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


def staff_position(letter: str, octave: int) -> int:
    return octave * 7 + LETTERS.index(letter)


def ledger_positions(pos: int) -> list[int]:
    """Staff positions of the ledger lines a note at ``pos`` needs."""
    if pos <= 28:
        return [q for q in range(28, pos - 1, -2)]
    if pos >= 40:
        return [q for q in range(40, pos + 1, 2)]
    return []


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


def _row_extent(pos: int) -> tuple[int, int]:
    """Highest and lowest staff positions drawn for a row (staff plus room for ledger lines)."""
    return max(39, pos + 2), min(29, pos - 2)


def _row_height(pos: int) -> float:
    top, bottom = _row_extent(pos)
    return (top - bottom) * STEP + 8 + DIAGRAM_SIZE + 22


def _staff(x: float, row_y: float, pos: int, accidental: str) -> list[str]:
    top, _bottom = _row_extent(pos)

    def y(p: float) -> float:
        return row_y + (top - p) * STEP + 2

    nx = x + NOTE_X
    out = [
        f'<line x1="{x + 2}" y1="{y(q):g}" x2="{x + 2 + STAFF_W}" y2="{y(q):g}" stroke="#000" stroke-width="0.7"/>'
        for q in LINE_POSITIONS
    ]
    out += [
        f'<line x1="{nx - 3:g}" y1="{y(q):g}" x2="{nx + 13:g}" y2="{y(q):g}" stroke="#000" stroke-width="0.7"/>'
        for q in ledger_positions(pos)
    ]
    glyph = lambda ch, gx, gy: (
        f'<text x="{gx:g}" y="{gy:g}" font-family="{MUSIC_FONT}" font-size="{MUSIC_FONT_SIZE}">{ch}</text>'
    )
    out.append(glyph(CLEF_G, x + 4, y(G_LINE)))
    if ACCIDENTAL_GLYPH[accidental]:
        out.append(glyph(ACCIDENTAL_GLYPH[accidental], nx - 11, y(pos)))
    out.append(glyph(NOTEHEAD_WHOLE, nx, y(pos)))
    return out


def _cell(db, letter, octave, cell, col, row_y, profile, alternates, lang, naming) -> str:
    accidental, _shift, midi = cell
    x = MARGIN + col * CELL_W
    pos = staff_position(letter, octave)
    pitch = midi_to_name(midi)
    top, bottom = _row_extent(pos)
    staff_h = (top - bottom) * STEP + 8
    label = note_label(letter, accidental, octave, naming)
    out = _staff(x, row_y, pos, accidental)
    out.append(
        f'<text x="{x + STAFF_W + 8}" y="{row_y + (top - G_LINE) * STEP + 6:g}" '
        f'font-size="13" font-weight="bold">{escape(label)}</text>'
    )
    found = _fingerings(db, pitch, profile, alternates)
    base_y = row_y + staff_h + DIAGRAM_SIZE
    if not found:
        out.append(
            f'<text x="{x + 6}" y="{base_y - 40:g}" font-size="10" fill="#888">{escape(TEXT[lang]["nodata"])}</text>'
        )
        return "\n".join(out)
    for i, f in enumerate(found):
        dx = x + 6 + i * DIAGRAM_STEP
        glyphs = escape(diagram_text(effective_keys(f, pitch)))
        out.append(
            f'<text x="{dx}" y="{base_y:g}" font-family="{FONT_FAMILY}" font-size="{DIAGRAM_SIZE}">{glyphs}</text>'
        )
        if f.category != Category.STANDARD:
            name = getattr(f.name, lang, None) or f.name.en
            out.append(
                f'<text x="{dx}" y="{base_y + 11:g}" font-size="7.5">{escape(name[:11])}</text>'
            )
    return "\n".join(out)


def _paginate(rows):
    pages, current, y = [], [], FIRST_ROW_Y
    for row in rows:
        height = _row_height(staff_position(row[0], row[1]))
        if current and y + height > PAGE_H - BOTTOM_MARGIN:
            pages.append(current)
            current, y = [], FIRST_ROW_Y
        current.append((row, y))
        y += height
    if current:
        pages.append(current)
    return pages


def chart_svg_pages(
    db: Database,
    profile: Profile | None = None,
    *,
    alternates: bool = False,
    lang: str = "en",
    naming: str = "letters",
    responsive: bool = False,
) -> list[str]:
    """SVG pages. ``responsive`` drops the fixed size and loads the fonts via @font-face (web)."""
    profile = profile or Profile()
    t = TEXT[lang]
    pages = []
    for page_rows in _paginate(chart_cells()):
        body = [
            f'<text x="{MARGIN}" y="55" font-size="24" font-weight="bold">{escape(t["title"])}</text>'
        ]
        for col, name in enumerate(t["cols"]):
            body.append(
                f'<text x="{MARGIN + col * CELL_W + 6}" y="{HEADER_Y}" font-size="13" fill="#555">{escape(name)}</text>'
            )
        for (letter, octave, cells), row_y in page_rows:
            body.append(
                f'<line x1="{MARGIN}" y1="{row_y - 4:g}" x2="{PAGE_W - MARGIN}" y2="{row_y - 4:g}" stroke="#ccc"/>'
            )
            for col, cell in enumerate(cells):
                if cell:
                    body.append(
                        _cell(
                            db, letter, octave, cell, col, row_y, profile, alternates, lang, naming
                        )
                    )
        body.append(
            f'<text x="{MARGIN}" y="{PAGE_H - 24}" font-size="9" fill="#666">{escape(t["note"])}</text>'
        )
        size = "" if responsive else f' width="{PAGE_W}" height="{PAGE_H}"'
        style = (
            "<style>@font-face{font-family:Fiati;src:url(/fonts/fiati-regular.ttf)}"
            "@font-face{font-family:Bravura;src:url(/fonts/Bravura.otf)}svg{background:#fff}</style>"
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
