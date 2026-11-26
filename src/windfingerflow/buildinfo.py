"""Build information and the small grey watermark put on every generated SVG/PDF page."""

from __future__ import annotations

import os
import re
import subprocess
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from windfingerflow import __version__

REPO_DIR = Path(__file__).resolve().parents[2]
MAX_WATERMARK_CHARS = 170


@cache
def git_sha() -> str:
    """Short sha1 of the running code: ``WFF_GIT_SHA`` (set at image build) or the local git checkout."""
    env = os.environ.get("WFF_GIT_SHA", "").strip()
    if env and env != "unknown":
        return env
    try:
        run = lambda *args: subprocess.run(
            ["git", "-C", str(REPO_DIR), *args],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        ).stdout.strip()
        sha = run("rev-parse", "--short=7", "HEAD")
        return f"{sha}-dirty" if run("status", "--porcelain") else sha
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def watermark_text(kind: str, **params: object) -> str:
    """``WindFingerFlow 0.0.1 (abc1234) - score - part=0 sax=alto ...``.

    Booleans appear as a bare flag when true; empty and false values are left out.
    """
    shown = []
    for key, value in params.items():
        if value is True:
            shown.append(key)
        elif value is not False and value is not None and value != "":  # 0 is a real value
            shown.append(f"{key}={value}")
    text = f"WindFingerFlow {__version__} ({git_sha()}) - {kind} - {' '.join(shown)}".rstrip(" -")
    return text if len(text) <= MAX_WATERMARK_CHARS else text[: MAX_WATERMARK_CHARS - 1] + "…"


_SVG_TAG = re.compile(r"<svg\b[^>]*>")
_WIDTH = re.compile(r'\swidth="([\d.]+)(?:px)?"')
_HEIGHT = re.compile(r'\sheight="([\d.]+)(?:px)?"')
_VIEWBOX = re.compile(r'viewBox="\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)\s*"')


def _page_size(svg: str) -> tuple[float, float] | None:
    tag = _SVG_TAG.search(svg)
    if not tag:
        return None
    root = tag.group(0)
    w, h = _WIDTH.search(root), _HEIGHT.search(root)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    box = _VIEWBOX.search(root)
    return (float(box.group(1)), float(box.group(2))) if box else None


def add_watermark(svg: str, text: str) -> str:
    """Add ``text`` as a small grey line at the bottom right of the page (last element drawn)."""
    size = _page_size(svg)
    end = svg.rfind("</svg>")
    if not text or size is None or end < 0:
        return svg
    w, h = size
    element = (
        f'<text x="{w * 0.975:.1f}" y="{h - h * 0.007:.1f}" text-anchor="end" '
        f'font-family="DejaVu Sans, sans-serif" font-size="{w / 115:.1f}" fill="#999" opacity="0.9">'
        f"{escape(text)}</text>"
    )
    return svg[:end] + element + svg[end:]
