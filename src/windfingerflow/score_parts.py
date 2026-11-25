"""List the parts of a score, to let the user pick one."""

from __future__ import annotations

from dataclasses import dataclass

from music21 import instrument, stream


@dataclass
class PartInfo:
    index: int
    name: str
    instrument: str
    notes: int
    is_sax: bool


def list_parts(score: stream.Score) -> list[PartInfo]:
    parts = list(getattr(score, "parts", None) or [score])
    out = []
    for i, part in enumerate(parts):
        inst = part.getInstrument(returnDefault=True)
        name = part.partName or inst.instrumentName or f"Part {i}"
        out.append(
            PartInfo(
                i,
                str(name),
                str(inst.instrumentName or ""),
                len(part.flatten().notes),
                isinstance(inst, instrument.Saxophone),
            )
        )
    return out


def default_part(parts: list[PartInfo]) -> int:
    """First saxophone part with notes, else the first part with notes, else 0."""
    for p in parts:
        if p.is_sax and p.notes:
            return p.index
    for p in parts:
        if p.notes:
            return p.index
    return 0
