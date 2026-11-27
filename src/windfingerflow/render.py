"""Render a MusicXML file to PDF with Verovio (SVG pages merged into one PDF)."""

from __future__ import annotations

import io
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from windfingerflow.buildinfo import add_watermark
from windfingerflow.fiati import DIAGRAM_SCALE, FONT_FAMILY, FONTS_DIR


def _use_bundled_fonts() -> None:
    """Make fontconfig (used by cairo) see the fonts in ``fonts/`` next to the system fonts.

    Must run before cairo is first used, hence before importing cairosvg.
    """
    tmp = Path(tempfile.gettempdir())
    conf = tmp / "windfingerflow-fonts.conf"
    conf.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
        '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
        f"  <dir>{FONTS_DIR}</dir>\n"
        f"  <cachedir>{tmp / 'windfingerflow-fc-cache'}</cachedir>\n"
        "</fontconfig>\n",
        encoding="utf-8",
    )
    os.environ["FONTCONFIG_FILE"] = str(conf)


_use_bundled_fonts()

import cairosvg
import verovio
from pypdf import PdfWriter

# The resource path is only right on the importing thread; capture it once and reuse it.
RESOURCE_PATH = verovio.toolkit().getResourcePath()

PAGE_OPTIONS = {
    "pageWidth": 2100,
    "pageHeight": 2970,
    "scale": 45,
    "pageMarginTop": 80,
    "pageMarginBottom": 80,
    "pageMarginLeft": 80,
    "pageMarginRight": 80,
    "breaks": "auto",
    "footer": "none",
    # more room around annotated notes: wider note spacing, and space above each system for the slanted texts
    "spacingLinear": 0.34,
    "spacingSystem": 16,
}


_PUA_TSPAN = re.compile(r'<tspan font-size="([^"]+)">([\ue000-\uf8ff]+)</tspan>')


def _tag_fiati(svg: str) -> str:
    """Verovio drops the font family and size of MusicXML <words>: restore them on Fiati runs."""

    def fix(m: re.Match) -> str:
        size = round(float(m.group(1).removesuffix("px")) * DIAGRAM_SCALE)
        return f'<tspan font-size="{size}px" font-family="{FONT_FAMILY}">{m.group(2)}</tspan>'

    return _PUA_TSPAN.sub(fix, svg)


ANNOTATION_SCALE = 0.62  # Verovio sets <words> in a large size: shrink the text annotations
ANNOTATION_ANGLE = (
    -45
)  # degrees: slanted text annotations do not overlap when several follow each other
_DIR_TEXT = re.compile(
    r'(<g id="[^"]*" class="dir">\s*)<text x="([\d.]+)" y="([\d.]+)"([^>]*)>(.*?)</text>', re.DOTALL
)


_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
_TRANSLATE = re.compile(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)")
ANNOTATION_GAP = (
    520  # Verovio units between the highest note (or staff line) and the annotation baseline
)


def _align_annotations(svg: str, gap: float = ANNOTATION_GAP) -> str:
    """Put every text annotation of a system on one baseline above its notes.

    Verovio staggers the annotations vertically as if they were horizontal, which makes the slanted
    texts of different lengths cross each other. On a common baseline they stay parallel.
    """
    root = ET.fromstring(svg)
    g_tag, text_tag, use_tag = f"{{{_SVG_NS}}}g", f"{{{_SVG_NS}}}text", f"{{{_SVG_NS}}}use"
    changed = False
    for system in root.iter(g_tag):
        if system.get("class") != "system":
            continue
        texts = []
        for d in system.iter(g_tag):
            if d.get("class") != "dir":
                continue
            for text in d.iter(text_tag):
                if not any(t.get("font-family") == FONT_FAMILY for t in text.iter()):
                    texts.append(text)
        if not texts:
            continue
        tops = []
        for head in system.iter(g_tag):
            if head.get("class") == "notehead":
                for use in head.iter(use_tag):
                    m = _TRANSLATE.search(use.get("transform", ""))
                    if m:
                        tops.append(float(m.group(2)))
        if not tops:
            continue
        baseline = min(tops) - gap
        for text in texts:
            text.set("y", f"{baseline:.0f}")
        changed = True
    if not changed:
        return svg
    out = ET.tostring(root, encoding="unicode")
    # keep Verovio's own root tag (attribute order matters to the code that rewrites it for the web)
    return svg[: svg.index(">") + 1] + out[out.index(">") + 1 :]


def _slant_annotations(svg: str, angle: float = ANNOTATION_ANGLE) -> str:
    """Rotate the text annotations around their start point (the Fiati diagrams stay upright)."""

    def fix(m: re.Match) -> str:
        head, x, y, attrs, body = m.groups()
        if FONT_FAMILY in body:
            return m.group(0)
        body = re.sub(
            r'font-size="([\d.]+)px"',
            lambda f: f'font-size="{float(f.group(1)) * ANNOTATION_SCALE:.0f}px"',
            body,
        )
        return f'{head}<text x="{x}" y="{y}"{attrs} transform="rotate({angle:g} {x} {y})">{body}</text>'

    return _DIR_TEXT.sub(fix, svg)


PREVIEW_OPTIONS = {**PAGE_OPTIONS, "adjustPageHeight": True}
_SVG_ROOT = re.compile(r'<svg width="([\d.]+)px" height="([\d.]+)px"')
_PREVIEW_STYLE = (
    "<style>@font-face{font-family:Fiati;src:url(/fonts/fiati-regular.ttf)}"
    "svg{background:#fff}</style>"
)


def render_preview_pages(
    musicxml: str | Path, watermark: str | None = None
) -> list[tuple[str, float, float]]:
    """Responsive SVG pages for the browser, as (svg, width, height).

    The root size is replaced by a viewBox so the page scales to its container, and the Fiati
    font is loaded through @font-face (the SVG is shown in an iframe, never inlined).
    """
    out = []
    for svg in render_svg_pages(musicxml, PREVIEW_OPTIONS, watermark):
        m = _SVG_ROOT.search(svg)
        if not m:
            raise ValueError("unexpected SVG root from Verovio")
        w, h = float(m.group(1)), float(m.group(2))
        svg = svg[: m.start()] + f'<svg viewBox="0 0 {w:g} {h:g}"' + svg[m.end() :]
        end_of_root = svg.index(">", m.start())
        svg = svg[: end_of_root + 1] + _PREVIEW_STYLE + svg[end_of_root + 1 :]
        out.append((svg, w, h))
    return out


def render_svg_pages(
    musicxml: str | Path, options: dict | None = None, watermark: str | None = None
) -> list[str]:
    tk = verovio.toolkit()
    tk.setResourcePath(RESOURCE_PATH)
    tk.setOptions(options or PAGE_OPTIONS)
    if not tk.loadFile(str(musicxml)):
        raise ValueError(f"Verovio could not read {musicxml}")
    pages = [
        _slant_annotations(_align_annotations(_tag_fiati(tk.renderToSVG(page))))
        for page in range(1, tk.getPageCount() + 1)
    ]
    return [add_watermark(p, watermark) for p in pages] if watermark else pages


def render_pdf(
    musicxml: str | Path,
    pdf: str | Path,
    extra_svg_pages: list[str] | None = None,
    watermark: str | None = None,
) -> int:
    """Write ``pdf`` from ``musicxml``; returns the number of pages."""
    pages = render_svg_pages(musicxml, None, watermark)
    writer = PdfWriter()
    for svg in [*pages, *(extra_svg_pages or [])]:
        buf = io.BytesIO()
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=buf)
        buf.seek(0)
        writer.append(buf)
    with open(pdf, "wb") as fh:
        writer.write(fh)
    return len(pages)


def write_pdf(svg_pages: list[str], pdf: str | Path) -> int:
    """Write already-built SVG pages (for example the fingering chart) to a PDF."""
    writer = PdfWriter()
    for svg in svg_pages:
        buf = io.BytesIO()
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=buf)
        buf.seek(0)
        writer.append(buf)
    with open(pdf, "wb") as fh:
        writer.write(fh)
    return len(svg_pages)
