"""Fingering chart over the whole range: one framed box per pitch, enharmonic spellings grouped.

Notes that sound the same share a fingering, so A sharp and B flat sit in one box: one staff with
all their spellings on the left and the standard fingering on the right. Alternate fingerings, when
asked for, go in a separate band under the staff, inside the same frame. Natural, flat, sharp, double
sharp and double flat spellings are covered. Pages are A4 landscape.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from windfingerflow.buildinfo import add_watermark
from windfingerflow.chooser import candidates, effective_keys
from windfingerflow.database import Database
from windfingerflow.fiati import FONT_FAMILY, diagram_text
from windfingerflow.instrument import ALTISSIMO_RANGE, WRITTEN_RANGE, midi_to_name
from windfingerflow.legend import fingering_color, legend_svg
from windfingerflow.models import Category, Fingering
from windfingerflow.profile import Profile

PAGE_W, PAGE_H = 1123, 794  # A4 landscape at 96 dpi
MARGIN = 40
COLUMNS = 3
GAP = 14
BOX_W = (PAGE_W - 2 * MARGIN - (COLUMNS - 1) * GAP) / COLUMNS
PAD = 8
FIRST_ROW_Y = 68
BOTTOM_MARGIN = 50
DIAGRAM_SIZE = 100
DIAGRAM_STEP = 42
MAX_STANDARD = 2
MAX_ALTERNATES = 3
ALT_NAME_CHARS = 10  # names printed under the alternate diagrams
LABEL_H = 20
NAME_H = 14  # alternate names printed under a diagram

# Staff geometry. Positions are diatonic steps: octave * 7 + letter index (C=0 ... B=6),
# so E4, the bottom line of the treble staff, is 30.
STAFF_SPACE = 6
STEP = STAFF_SPACE / 2
CLEF_W = 28
NOTE_SPACING = 30
STAFF_MAX_W = CLEF_W + NOTE_SPACING * 3 + 4  # diagrams start to the right of the widest staff
LINE_POSITIONS = (30, 32, 34, 36, 38)
G_LINE = 32
MUSIC_FONT = "Bravura"
MUSIC_FONT_SIZE = 4 * STAFF_SPACE  # SMuFL: a font size of four staff spaces
CLEF_G = "\ue050"
NOTEHEAD_WHOLE = "\ue0a2"
# Distance from the left edge of the accidental to the note head, so each sign sits right against its
# own note (Bravura advances: flat 0.9, sharp 1.0, double sharp 1.0, double flat 1.6 staff spaces).
ACCIDENTAL_OFFSET = {"♭": 7.5, "♯": 8, "♯♯": 8, "♭♭": 11.5}
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
        "note": "Notes that sound the same share a box. Altissimo (above F#6) only when asked. "
        "Alternates follow the standard fingering, with their name.",
    },
    "fr": {
        "title": "Tableau de doigtés de saxophone (hauteur écrite)",
        "nodata": "pas de données",
        "note": "Les notes qui sonnent pareil partagent un cadre. Suraigu (au-dessus du Fa#6) seulement sur demande. "
        "Les alternatives suivent le doigté standard, avec leur nom.",
    },
}

Spelling = tuple[str, str, int]  # letter, accidental, octave
Group = tuple[int, list[Spelling]]  # midi, spellings
Entry = tuple[Group, list[Fingering], list[Fingering]]  # group, standard fingerings, alternates


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


def pitch_groups(altissimo: bool = False) -> list[Group]:
    """Every pitch of the written range with all its spellings, lowest pitch first.

    Spellings are ordered from the lowest to the highest staff position.
    """
    low, high = WRITTEN_RANGE
    if altissimo:
        high = ALTISSIMO_RANGE[1]
    groups: dict[int, list[Spelling]] = {}
    for octave in range(3, 8):
        for letter in LETTERS:
            for accidental, shift in ACCIDENTALS:
                midi = (octave + 1) * 12 + BASE[letter] + shift
                if low <= midi <= high:
                    groups.setdefault(midi, []).append((letter, accidental, octave))
    return [
        (midi, sorted(spellings, key=lambda s: staff_position(s[0], s[2])))
        for midi, spellings in sorted(groups.items())
    ]


def _fingerings(
    db: Database, pitch: str, profile: Profile, alternates: bool
) -> tuple[list[Fingering], list[Fingering]]:
    """(standard fingerings, alternates). Alternates are only returned when asked for."""
    found = candidates(db, pitch, profile)
    found.sort(key=lambda f: f.id)
    standard = [f for f in found if f.category == Category.STANDARD][:MAX_STANDARD]
    extra = (
        [f for f in found if f.category != Category.STANDARD][:MAX_ALTERNATES] if alternates else []
    )
    return standard, extra


def _row_extent(row: list[Entry]) -> tuple[int, int]:
    """Highest and lowest staff positions drawn for a row (staff plus room for ledger lines)."""
    positions = [staff_position(s[0], s[2]) for (_, spellings), _, _ in row for s in spellings]
    return max(39, max(positions) + 2), min(29, min(positions) - 2)


def _staff_height(row: list[Entry]) -> float:
    top, bottom = _row_extent(row)
    return (top - bottom) * STEP + 8


def _top_height(row: list[Entry]) -> float:
    """Height of the box content: the staff with its label, or the diagrams (with alternate names)."""
    names = NAME_H if any(alts for _, _, alts in row) else 0
    return max(_staff_height(row) + LABEL_H, DIAGRAM_SIZE + names)


def _box_height(row: list[Entry]) -> float:
    return _top_height(row) + 2 * PAD


def _glyph(ch: str, x: float, y: float) -> str:
    return f'<text x="{x:g}" y="{y:g}" font-family="{MUSIC_FONT}" font-size="{MUSIC_FONT_SIZE}">{ch}</text>'


def _staff(x: float, staff_top: float, top: int, spellings: list[Spelling]) -> list[str]:
    def y(p: float) -> float:
        return staff_top + (top - p) * STEP + 2

    width = CLEF_W + NOTE_SPACING * len(spellings) + 4
    out = [
        f'<line x1="{x:g}" y1="{y(q):g}" x2="{x + width:g}" y2="{y(q):g}" stroke="#000" stroke-width="0.7"/>'
        for q in LINE_POSITIONS
    ]
    out.append(_glyph(CLEF_G, x + 2, y(G_LINE)))
    for k, (letter, accidental, octave) in enumerate(spellings):
        pos = staff_position(letter, octave)
        nx = x + CLEF_W + 12 + k * NOTE_SPACING
        out += [
            f'<line x1="{nx - 3:g}" y1="{y(q):g}" x2="{nx + 13:g}" y2="{y(q):g}" stroke="#000" stroke-width="0.7"/>'
            for q in ledger_positions(pos)
        ]
        if ACCIDENTAL_GLYPH[accidental]:
            out.append(
                _glyph(ACCIDENTAL_GLYPH[accidental], nx - ACCIDENTAL_OFFSET[accidental], y(pos))
            )
        out.append(_glyph(NOTEHEAD_WHOLE, nx, y(pos)))
    return out


def _cell(entry, col, box_y, row, lang, naming) -> str:
    (midi, spellings), standard, alternates = entry
    box_x = MARGIN + col * (BOX_W + GAP)
    box_h = _box_height(row)
    top, _bottom = _row_extent(row)
    staff_h = _staff_height(row)
    pitch = midi_to_name(midi)
    out = [
        (
            f'<rect x="{box_x:g}" y="{box_y:g}" width="{BOX_W:g}" height="{box_h:g}" rx="5" '
            'fill="none" stroke="#888" stroke-width="1"/>'
        )
    ]
    # Staff and label on the left, vertically centred in the box.
    staff_top = box_y + (box_h - (staff_h + LABEL_H)) / 2
    sx = box_x + PAD
    out += _staff(sx, staff_top, top, spellings)
    label = " / ".join(note_label(*s[:2], s[2], naming) for s in spellings)
    out.append(
        f'<text x="{sx:g}" y="{staff_top + staff_h + 13:g}" font-size="10" font-weight="bold">{escape(label)}</text>'
    )
    # Diagrams to the right of the staff: the standard fingering first, then the alternates.
    dx0 = box_x + PAD + STAFF_MAX_W + 14
    base_y = box_y + PAD + DIAGRAM_SIZE
    shown = [(f, False) for f in standard] + [(f, True) for f in alternates]
    if not shown:
        out.append(
            f'<text x="{dx0:g}" y="{box_y + box_h / 2:g}" font-size="10" fill="#888">'
            f"{escape(TEXT[lang]['nodata'])}</text>"
        )
        return "\n".join(out)
    step = min(DIAGRAM_STEP, (box_x + BOX_W - PAD - dx0) / len(shown))
    for i, (f, is_alternate) in enumerate(shown):
        dx = dx0 + i * step
        glyphs = escape(diagram_text(effective_keys(f, pitch)))
        out.append(
            f'<text x="{dx:g}" y="{base_y:g}" font-family="{FONT_FAMILY}" font-size="{DIAGRAM_SIZE}">{glyphs}</text>'
        )
        if is_alternate:
            name = getattr(f.name, lang, None) or f.name.en
            out.append(
                f'<text x="{dx:g}" y="{base_y + 11:g}" font-size="7.5" '
                f'fill="{fingering_color(f)}">{escape(name[:ALT_NAME_CHARS])}</text>'
            )
    if standard and alternates:
        sep = dx0 + len(standard) * step - 4
        out.append(
            f'<line x1="{sep:g}" y1="{box_y + PAD:g}" x2="{sep:g}" y2="{base_y + NAME_H - 4:g}" '
            'stroke="#bbb" stroke-dasharray="3 3"/>'
        )
    return "\n".join(out)


def _rows(db: Database, profile: Profile, alternates: bool) -> list[list[Entry]]:
    entries: list[Entry] = []
    for group in pitch_groups(profile.allow_altissimo):
        standard, extra = _fingerings(db, midi_to_name(group[0]), profile, alternates)
        entries.append((group, standard, extra))
    return [entries[i : i + COLUMNS] for i in range(0, len(entries), COLUMNS)]


def _paginate(rows):
    pages, current, y = [], [], FIRST_ROW_Y
    for row in rows:
        height = _box_height(row)
        if current and y + height > PAGE_H - BOTTOM_MARGIN:
            pages.append(current)
            current, y = [], FIRST_ROW_Y
        current.append((row, y))
        y += height + GAP
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
    watermark: str | None = None,
) -> list[str]:
    """SVG pages. ``responsive`` drops the fixed size and loads the fonts via @font-face (web)."""
    profile = profile or Profile()
    t = TEXT[lang]
    pages = []
    for page_rows in _paginate(_rows(db, profile, alternates)):
        body = [
            f'<text x="{MARGIN}" y="42" font-size="22" font-weight="bold">{escape(t["title"])}</text>'
        ]
        for row, box_y in page_rows:
            for col, entry in enumerate(row):
                body.append(_cell(entry, col, box_y, row, lang, naming))
        if alternates:
            body.append(legend_svg(MARGIN, PAGE_H - 36, lang))
        body.append(
            f'<text x="{MARGIN}" y="{PAGE_H - 22}" font-size="9" fill="#666">{escape(t["note"])}</text>'
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
    return [add_watermark(p, watermark) for p in pages] if watermark else pages
