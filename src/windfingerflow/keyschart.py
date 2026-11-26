"""Key reference page: every key of the catalogue drawn alone on the diagram, with its names."""

from __future__ import annotations

import textwrap
from xml.sax.saxutils import escape

from windfingerflow.buildinfo import add_watermark
from windfingerflow.database import Database
from windfingerflow.fiati import FONT_FAMILY, diagram_markup
from windfingerflow.i18n import ui
from windfingerflow.models import Key

PAGE_W, PAGE_H = 1123, 794  # A4 landscape at 96 dpi
MARGIN = 40
COLUMNS = 3
GAP = 14
BOX_W = (PAGE_W - 2 * MARGIN - (COLUMNS - 1) * GAP) / COLUMNS
PAD = 8
FIRST_ROW_Y = 68
BOTTOM_MARGIN = 40
DIAGRAM_SIZE = 100
TEXT_X = 62  # text column, to the right of the diagram
WRAP_CHARS = 44
LINE_H = 14


def key_lines(key: Key, lang: str) -> list[tuple[str, str]]:
    """Text lines of a key box as (style, text); style is one of id, name, name2, info, small, flag."""
    t = ui(lang, "keys_page")
    # The name in the page language is the bold one; the other language follows in italics.
    first = key.name.get(lang)
    second = key.name.get("fr") if lang == "en" else key.name.get("en")
    abbr = key.abbr.get(lang)
    if abbr:
        first = f"{abbr} - {first}"
    lines = [("id", key.id), ("name", first), ("name2", second)]
    lines.append(
        ("info", f"{t['finger']} {key.finger.value} - {t['group']}: {t['groups'][key.group.value]}")
    )
    lines.append(("info", f"{t['availability']}: {key.availability.get(lang)}"))
    for part in textwrap.wrap(key.description.get(lang), WRAP_CHARS):
        lines.append(("small", part))
    if key.needs_confirmation:
        lines.append(("flag", t["confirm"]))
    return [(style, text) for style, text in lines if text]


def _box_height(key: Key, lang: str) -> float:
    return max(DIAGRAM_SIZE, len(key_lines(key, lang)) * LINE_H + 4) + 2 * PAD


STYLES = {
    "id": 'font-family="DejaVu Sans Mono, monospace" font-size="11" fill="#555"',
    "name": 'font-size="13" font-weight="bold"',
    "name2": 'font-size="12" font-style="italic"',
    "info": 'font-size="10.5"',
    "small": 'font-size="9.5" fill="#555"',
    "flag": 'font-size="10.5" font-weight="bold" fill="#b03a00"',
}


def _box(key: Key, col: int, y: float, height: float, lang: str) -> str:
    x = MARGIN + col * (BOX_W + GAP)
    out = [
        f'<rect x="{x:g}" y="{y:g}" width="{BOX_W:g}" height="{height:g}" rx="5" fill="none" stroke="#888"/>',
        (
            f'<text x="{x + PAD:g}" y="{y + PAD + DIAGRAM_SIZE:g}" font-family="{FONT_FAMILY}" '
            f'font-size="{DIAGRAM_SIZE}">{diagram_markup([key.id])}</text>'
        ),
    ]
    ty = y + PAD + 11
    for style, text in key_lines(key, lang):
        out.append(
            f'<text x="{x + PAD + TEXT_X:g}" y="{ty:g}" {STYLES[style]}>{escape(text)}</text>'
        )
        ty += LINE_H
    return "\n".join(out)


def _paginate(keys: list[Key], lang: str):
    """Rows of COLUMNS keys, packed onto pages by height: [[(row_keys, y, height), ...], ...]."""
    pages, current, y = [], [], FIRST_ROW_Y
    for i in range(0, len(keys), COLUMNS):
        row = keys[i : i + COLUMNS]
        height = max(_box_height(k, lang) for k in row)
        if current and y + height > PAGE_H - BOTTOM_MARGIN:
            pages.append(current)
            current, y = [], FIRST_ROW_Y
        current.append((row, y, height))
        y += height + GAP
    if current:
        pages.append(current)
    return pages


def keys_svg_pages(
    db: Database, *, lang: str = "en", responsive: bool = False, watermark: str | None = None
) -> list[str]:
    t = ui(lang, "keys_page")
    pages = []
    for page_rows in _paginate(list(db.keys.values()), lang):
        body = [
            f'<text x="{MARGIN}" y="42" font-size="22" font-weight="bold">{escape(t["title"])}</text>'
        ]
        for row, y, height in page_rows:
            for col, key in enumerate(row):
                body.append(_box(key, col, y, height, lang))
        body.append(
            f'<text x="{MARGIN}" y="{PAGE_H - 22}" font-size="9" fill="#666">{escape(t["legend"])}</text>'
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
    return [add_watermark(p, watermark) for p in pages] if watermark else pages
