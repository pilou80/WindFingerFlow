"""The project logo (``web/static/logo.svg``), also drawn on the generated pages."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

LOGO_PATH = Path(__file__).parent / "web" / "static" / "logo.svg"
LOGO_VIEWBOX = 64


@lru_cache(maxsize=1)
def _logo_body() -> str:
    svg = LOGO_PATH.read_text(encoding="utf-8")
    match = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.DOTALL)
    return match.group(1).strip() if match else ""


def logo_markup(x: float, y: float, size: float) -> str:
    """The logo as an SVG group placed with its top-left corner at (x, y)."""
    scale = size / LOGO_VIEWBOX
    return (
        f'<g id="wff-logo" transform="translate({x:g} {y:g}) scale({scale:g})">{_logo_body()}</g>'
    )
