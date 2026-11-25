"""Annotate the score with the chosen fingerings (text only for now)."""

from __future__ import annotations

from music21 import expressions, stream

from windfingerflow.models import Category, Fingering
from windfingerflow.score import NoteEvent


def annotate(
    events: list[NoteEvent],
    chosen: list[Fingering | None],
    lang: str = "en",
    all_notes: bool = False,
) -> int:
    """Add a text expression above each annotated note; returns how many were added."""
    count = 0
    for event, fingering in zip(events, chosen, strict=True):
        if fingering is None:
            continue
        if not all_notes and fingering.category == Category.STANDARD:
            continue
        text = getattr(fingering.name, lang, None) or fingering.name.en
        # Insert into the real container (the measure), not the flattened view.
        container = event.element.getContextByClass(stream.Measure) or event.element.activeSite
        offset = event.element.getOffsetBySite(container)
        expression = expressions.TextExpression(text)
        expression.placement = "above"
        container.insert(offset, expression)
        count += 1
    return count
