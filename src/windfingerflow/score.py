"""Read a score and extract one monophonic line (written pitch assumed)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from music21 import converter, note, stream


@dataclass
class NoteEvent:
    element: note.NotRest  # the music21 note or chord, kept for annotation
    pitch: str  # e.g. "Bb4", "F#4"
    duration: float  # quarter lengths
    is_chord: bool = False


def pitch_name(p) -> str:
    """music21 pitch -> our notation (``B-4`` becomes ``Bb4``)."""
    return f"{p.name.replace('-', 'b')}{p.octave}"


def load_score(path: str | Path) -> stream.Score:
    parsed = converter.parse(str(path))
    if isinstance(parsed, stream.Score):
        return parsed
    score = stream.Score()
    score.insert(0, parsed)
    return score


def extract_line(score: stream.Score, part_index: int = 0) -> list[NoteEvent]:
    """Notes of one part; for chords, only the top note is kept (top-voice rule)."""
    parts = getattr(score, "parts", None)
    part = parts[part_index] if parts else score
    events: list[NoteEvent] = []
    for el in part.flatten().notes:
        if el.isChord:
            top = max(el.pitches, key=lambda p: p.midi)
            events.append(NoteEvent(el, pitch_name(top), float(el.quarterLength), True))
        else:
            events.append(NoteEvent(el, pitch_name(el.pitch), float(el.quarterLength)))
    return events
