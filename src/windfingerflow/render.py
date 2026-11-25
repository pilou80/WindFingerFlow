"""Render a MusicXML file to PDF with Verovio (SVG pages merged into one PDF)."""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
import verovio
from pypdf import PdfWriter

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
}


def render_pdf(musicxml: str | Path, pdf: str | Path) -> int:
    """Write ``pdf`` from ``musicxml``; returns the number of pages."""
    tk = verovio.toolkit()
    tk.setOptions(PAGE_OPTIONS)
    if not tk.loadFile(str(musicxml)):
        raise ValueError(f"Verovio could not read {musicxml}")
    writer = PdfWriter()
    pages = tk.getPageCount()
    for page in range(1, pages + 1):
        svg = tk.renderToSVG(page)
        buf = io.BytesIO()
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=buf)
        buf.seek(0)
        writer.append(buf)
    with open(pdf, "wb") as fh:
        writer.write(fh)
    return pages
