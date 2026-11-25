"""Read a score and extract one monophonic line, converted to written sax pitch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from music21 import converter, instrument, note, stream

from windfingerflow.instrument import SAX_OFFSET, in_written_range, midi_to_name


@dataclass
class NoteEvent:
    element: note.NotRest  # the music21 note or chord, kept for annotation
    pitch: str  # written pitch, e.g. "Bb4", "F#4"
    duration: float  # quarter lengths
    midi: int
    is_chord: bool = False
    measure: int | None = None


def load_score(path: str | Path) -> stream.Score:
    parsed = converter.parse(str(path))
    if isinstance(parsed, stream.Score):
        return parsed
    score = stream.Score()
    score.insert(0, parsed)
    return score


def extract_line(
    score: stream.Score, part_index: int = 0, target_sax: str | None = None
) -> list[NoteEvent]:
    """Notes of one part, as written pitch.

    - ``target_sax=None``: keep the part as written (a sax part stays as is, a non-transposing
      part is read as is).
    - ``target_sax="alto"`` etc.: convert the sounding pitch to that saxophone's written pitch.
    Chords keep only their top note (top-voice rule).
    """
    parts = getattr(score, "parts", None)
    part = parts[part_index] if parts else score
    inst = part.getInstrument(returnDefault=True)
    transposition = inst.transposition.semitones if inst.transposition is not None else 0
    in_file_is_sounding = getattr(part, "atSoundingPitch", "unknown") is True
    to_sounding = 0 if in_file_is_sounding else transposition

    events: list[NoteEvent] = []
    for el in part.flatten().notes:
        top = max(el.pitches, key=lambda p: p.midi) if el.isChord else el.pitch
        sounding = top.midi + to_sounding
        written = sounding + SAX_OFFSET[target_sax] if target_sax else sounding - transposition
        events.append(
            NoteEvent(
                el,
                midi_to_name(written),
                float(el.quarterLength),
                written,
                el.isChord,
                el.measureNumber,
            )
        )
    return events


def is_sax_part(part: stream.Stream) -> bool:
    return isinstance(part.getInstrument(returnDefault=True), instrument.Saxophone)


def range_warnings(events: list[NoteEvent]) -> list[str]:
    out = []
    for e in events:
        if not in_written_range(e.midi):
            out.append(f"{e.pitch} (offset {e.element.offset}) is outside the written sax range")
        if e.is_chord:
            out.append(f"chord at offset {e.element.offset}: only the top note ({e.pitch}) is used")
    return out
