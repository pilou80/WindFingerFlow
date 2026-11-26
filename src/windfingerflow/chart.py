"""Fingering chart over the whole range: one cell per pitch, enharmonic spellings grouped.

Notes that sound the same share a fingering, so A sharp and B flat sit in one cell: one staff with
both spellings and one set of diagrams. Natural, flat, sharp, double sharp and double flat are covered.
"""

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
COLUMNS = 4
CELL_W = 178
FIRST_ROW_Y = 85
BOTTOM_MARGIN = 50
DIAGRAM_SIZE = 100
DIAGRAM_STEP = 42
MAX_DIAGRAMS = 4
LABEL_H = 22

# Staff geometry. Positions are diatonic steps: octave * 7 + letter index (C=0 ... B=6),
# so E4, the bottom line of the treble staff, is 30.
STAFF_SPACE = 6
STEP = STAFF_SPACE / 2
CLEF_W = 28
NOTE_SPACING = 38  # room for a note's own accidental before the next note head
LINE_POSITIONS = (30, 32, 34, 36, 38)
G_LINE = 32
MUSIC_FONT = "Bravura"
MUSIC_FONT_SIZE = 4 * STAFF_SPACE  # SMuFL: a font size of four staff spaces
CLEF_G = "\ue050"
NOTEHEAD_WHOLE = "\ue0a2"
HIGHLIGHT_COLOR = "#d35400"  # the middle note of a three-spelling cell
ACCIDENTAL_GLYPH = {"": "", "♭": "\ue260", "♯": "\ue262", "♯♯": "\ue263", "♭♭": "\ue264"}

LETTERS = ["C", "D", "E", "F", "G", "A", "B"]
BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SOLFEGE = {"C": "Do", "D": "Ré", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}
# (accidental label, semitone shift); doubles are written with two signs (font-safe in the labels).
ACCIDENTALS = [("", 0), ("♭", -1), ("♯", 1), ("♯♯", 2), ("♭♭", -2)]

TEXT = {
    "en": {
        "title": "Saxophone fingering chart (written pitch)",
        "nodata": "no data",
        "note": "Notes that sound the same share a cell. Altissimo above F#6 is not covered. "
        "Alternates are named under the diagram.",
    },
    "fr": {
        "title": "Tableau de doigtés de saxophone (hauteur écrite)",
        "nodata": "pas de données",
        "note": "Les notes qui sonnent pareil partagent une case. Suraigu au-dessus du Fa#6 "
        "non couvert. Les alternatives sont nommées sous le diagramme.",
    },
}

Spelling = tuple[str, str, int]  # letter, accidental, octave


def note_label(letter: str, accidental: str, octave: int, naming: str) -> str:
    name = SOLFEGE[letter] if naming == "solfege" else letter
    return f"{name}{accidental}{octave}"


def staff_position(letter: str, octave: int) -> int:
    return octave * 7 + LETTERS.index(letter)


def ledger_positions(pos: int) -> list[int]:
    """Staff positions of the ledger lines a note at ``pos`` needs."""
    if pos <= 28:
        return list(range(28, pos - 1, -2))
    if pos >= 40:
        return list(range(40, pos + 1, 2))
    return []


def pitch_groups() -> list[tuple[int, list[Spelling]]]:
    """Every pitch of the written range with all its spellings, lowest pitch first.

    Spellings are ordered from the lowest to the highest staff position.
    """
    low, high = WRITTEN_RANGE
    groups: dict[int, list[Spelling]] = {}
    for octave in range(3, 7):
        for letter in LETTERS:
            for accidental, shift in ACCIDENTALS:
                midi = (octave + 1) * 12 + BASE[letter] + shift
                if low <= midi <= high:
                    groups.setdefault(midi, []).append((letter, accidental, octave))
    return [
        (midi, sorted(spellings, key=lambda s: staff_position(s[0], s[2])))
        for midi, spellings in sorted(groups.items())
    ]


def _fingerings(db: Database, pitch: str, profile: Profile, alternates: bool) -> list[Fingering]:
    found = candidates(db, pitch, profile)
    found.sort(key=lambda f: (f.category != Category.STANDARD, f.id))
    if not alternates:
        found = [f for f in found if f.category == Category.STANDARD]
    return found[:MAX_DIAGRAMS]


def _row_extent(row: list[tuple[int, list[Spelling]]]) -> tuple[int, int]:
    """Highest and lowest staff positions drawn for a row (staff plus room for ledger lines)."""
    positions = [staff_position(s[0], s[2]) for _, spellings in row for s in spellings]
    return max(39, max(positions) + 2), min(29, min(positions) - 2)


def _staff_height(row) -> float:
    top, bottom = _row_extent(row)
    return (top - bottom) * STEP + 8


def _row_height(row) -> float:
    return _staff_height(row) + LABEL_H + DIAGRAM_SIZE + 22


def highlighted_index(spellings: list[Spelling]) -> int | None:
    """Index of the spelling drawn in colour: the middle note of a cell with three spellings."""
    return len(spellings) // 2 if len(spellings) == 3 else None


def _glyph(ch: str, x: float, y: float, fill: str | None = None) -> str:
    color = f' fill="{fill}"' if fill else ""
    return f'<text x="{x:g}" y="{y:g}" font-family="{MUSIC_FONT}" font-size="{MUSIC_FONT_SIZE}"{color}>{ch}</text>'


def _staff(x: float, row_y: float, top: int, spellings: list[Spelling]) -> list[str]:
    def y(p: float) -> float:
        return row_y + (top - p) * STEP + 2

    width = CLEF_W + NOTE_SPACING * len(spellings) + 4
    out = [
        f'<line x1="{x + 2}" y1="{y(q):g}" x2="{x + 2 + width}" y2="{y(q):g}" stroke="#000" stroke-width="0.7"/>'
        for q in LINE_POSITIONS
    ]
    out.append(_glyph(CLEF_G, x + 4, y(G_LINE)))
    highlight = highlighted_index(spellings)
    for k, (letter, accidental, octave) in enumerate(spellings):
        fill = HIGHLIGHT_COLOR if k == highlight else None
        pos = staff_position(letter, octave)
        nx = x + CLEF_W + 14 + k * NOTE_SPACING
        out += [
            f'<line x1="{nx - 3:g}" y1="{y(q):g}" x2="{nx + 13:g}" y2="{y(q):g}" stroke="#000" stroke-width="0.7"/>'
            for q in ledger_positions(pos)
        ]
        if ACCIDENTAL_GLYPH[accidental]:
            out.append(
                _glyph(
                    ACCIDENTAL_GLYPH[accidental],
                    nx - (14 if len(accidental) > 1 else 11),
                    y(pos),
                    fill,
                )
            )
        out.append(_glyph(NOTEHEAD_WHOLE, nx, y(pos), fill))
    return out


def _cell(db, group, col, row_y, row, profile, alternates, lang, naming) -> str:
    midi, spellings = group
    x = MARGIN + col * CELL_W
    top, _bottom = _row_extent(row)
    staff_h = _staff_height(row)
    pitch = midi_to_name(midi)
    out = _staff(x, row_y, top, spellings)
    highlight = highlighted_index(spellings)
    parts = []
    for k, s in enumerate(spellings):
        name = escape(note_label(*s[:2], s[2], naming))
        parts.append(f'<tspan fill="{HIGHLIGHT_COLOR}">{name}</tspan>' if k == highlight else name)
    out.append(
        f'<text x="{x + 4}" y="{row_y + staff_h + 14:g}" font-size="11" font-weight="bold">'
        + " / ".join(parts)
        + "</text>"
    )
    found = _fingerings(db, pitch, profile, alternates)
    base_y = row_y + staff_h + LABEL_H + DIAGRAM_SIZE
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


def _rows() -> list[list[tuple[int, list[Spelling]]]]:
    groups = pitch_groups()
    return [groups[i : i + COLUMNS] for i in range(0, len(groups), COLUMNS)]


def _paginate(rows):
    pages, current, y = [], [], FIRST_ROW_Y
    for row in rows:
        height = _row_height(row)
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
    for page_rows in _paginate(_rows()):
        body = [
            f'<text x="{MARGIN}" y="55" font-size="24" font-weight="bold">{escape(t["title"])}</text>'
        ]
        for row, row_y in page_rows:
            body.append(
                f'<line x1="{MARGIN}" y1="{row_y - 4:g}" x2="{PAGE_W - MARGIN}" y2="{row_y - 4:g}" stroke="#ccc"/>'
            )
            for col, group in enumerate(row):
                body.append(_cell(db, group, col, row_y, row, profile, alternates, lang, naming))
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
