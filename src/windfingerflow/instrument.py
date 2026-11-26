"""Saxophone facts: transposition, written range and register rules (midi numbers)."""

from __future__ import annotations

from windfingerflow.models import parse_pitch

# Semitones to add to the sounding (concert) pitch to get the written pitch.
SAX_OFFSET = {"soprano": 2, "alto": 9, "tenor": 14, "baritone": 21}
WRITTEN_RANGE = (58, 90)  # written low Bb3 .. high F#6 (generic model)
OCTAVE_KEY_RANGE = (74, 90)  # written D5 .. F#6 use the octave key (assumed for the palm keys)

_NAMES = {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5: "F", 6: "F#", 7: "G", 8: "G#", 9: "A"}
_NAMES |= {10: "Bb", 11: "B"}
_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi_to_name(midi: int) -> str:
    """Canonical spelling (Eb, Bb, C#, F#, G#) so enharmonics hit the same data."""
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def name_to_midi(name: str) -> int:
    letter, accidental, octave = parse_pitch(name)
    shift = {"": 0, "#": 1, "b": -1}[accidental]
    return (octave + 1) * 12 + _BASE[letter] + shift


def needs_octave_key(pitch: str) -> bool:
    low, high = OCTAVE_KEY_RANGE
    return low <= name_to_midi(pitch) <= high


def in_written_range(midi: int) -> bool:
    return WRITTEN_RANGE[0] <= midi <= WRITTEN_RANGE[1]
