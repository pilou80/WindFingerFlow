"""Annotate the score with the chosen fingerings: text, Fiati diagrams, or both."""

from __future__ import annotations

from music21 import expressions, stream

from windfingerflow.chooser import effective_keys
from windfingerflow.fiati import FONT_FAMILY, diagram_text
from windfingerflow.models import Category, Fingering
from windfingerflow.score import NoteEvent

STYLES = ("text", "diagram", "both")


def _add(event: NoteEvent, expression: expressions.TextExpression) -> None:
    expression.placement = "above"
    # Insert into the real container (the measure), not the flattened view.
    container = event.element.getContextByClass(stream.Measure) or event.element.activeSite
    container.insert(event.element.getOffsetBySite(container), expression)


def annotate(
    events: list[NoteEvent],
    chosen: list[Fingering | None],
    lang: str = "en",
    all_notes: bool = False,
    style: str = "text",
) -> int:
    """Annotate the chosen fingerings above the notes; returns how many notes were annotated."""
    if style not in STYLES:
        raise ValueError(f"unknown annotation style {style!r}")
    count = 0
    for event, fingering in zip(events, chosen, strict=True):
        if fingering is None:
            continue
        if not all_notes and fingering.category == Category.STANDARD:
            continue
        if style in ("diagram", "both"):
            diagram = expressions.TextExpression(
                diagram_text(effective_keys(fingering, event.pitch))
            )
            diagram.style.fontFamily = FONT_FAMILY
            _add(event, diagram)
        if style in ("text", "both"):
            text = fingering.name.get(lang)
            _add(event, expressions.TextExpression(text))
        count += 1
    return count
