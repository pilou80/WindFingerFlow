"""Pydantic models for the key catalogue and the fingering database."""

from __future__ import annotations

import datetime
import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

KeyId = Annotated[str, StringConstraints(pattern=r"^(lh|rh|cc)\.[a-z0-9_]+$")]
FingeringId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+\.[a-z0-9_]+$")]
Pitch = Annotated[str, StringConstraints(pattern=r"^[A-G](#|b)?-?[0-9]$")]


class Finger(StrEnum):
    LT = "LT"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"


class KeyGroup(StrEnum):
    MAIN = "main"
    PALM = "palm"
    SIDE = "side"
    PINKY = "pinky"
    THUMB = "thumb"
    OCTAVE = "octave"


class Category(StrEnum):
    STANDARD = "standard"
    ALTERNATE = "alternate"
    ALTISSIMO = "altissimo"
    TRILL = "trill"


class Level(StrEnum):
    BEGINNER = "beginner"
    ADVANCED = "advanced"
    EXPERT = "expert"
    EXPERIMENTAL = "experimental"  # fingerings the saxophonist found unreliable or unproven


LEVEL_RANK = {Level.BEGINNER: 0, Level.ADVANCED: 1, Level.EXPERT: 2, Level.EXPERIMENTAL: 3}


class Intonation(StrEnum):
    REFERENCE = "reference"
    IN_TUNE = "in_tune"
    SHARP = "sharp"
    FLAT = "flat"
    UNKNOWN = "unknown"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class I18n(Strict):
    """Translatable text: one string per language code, English as the fallback."""

    texts: dict[str, str] = Field(default_factory=dict)

    def get(self, lang: str) -> str:
        return self.texts.get(lang) or self.texts.get("en") or ""

    @property
    def en(self) -> str:
        return self.texts.get("en", "")


class LilyPondKey(Strict):
    group: str  # cc, lh or rh
    name: str


class Key(Strict):
    id: KeyId
    # Texts come from data/<instrument>/translations/<lang>.yaml, not from the key catalogue.
    name: I18n = Field(default_factory=I18n)
    abbr: I18n = Field(default_factory=I18n)  # short notation (French: C1, C2, C3, Ta, Tc, Tf)
    finger: Finger
    substitute_fingers: list[Finger] = Field(default_factory=list)
    group: KeyGroup
    lilypond: LilyPondKey | None = None
    availability: I18n = Field(default_factory=I18n)
    description: I18n = Field(default_factory=I18n)
    needs_confirmation: bool = False  # data still to verify (see design notes §13)


class KeyCatalogue(Strict):
    family: str
    keys: list[Key]

    def by_id(self) -> dict[str, Key]:
        return {k.id: k for k in self.keys}


class Source(Strict):
    name: str
    url: str | None = None


class Fingering(Strict):
    id: FingeringId
    name: I18n = Field(default_factory=I18n)  # from the translation files
    pitches: list[Pitch] = Field(min_length=1)  # written pitches
    # Keys pressed in the lower register. The octave key is added by the
    # instrument's register rules, so it is not listed here.
    keys: list[KeyId]
    category: Category
    level: Level
    intonation: Intonation = Intonation.UNKNOWN
    cents: float | None = None  # computed from the trial files (mean of the measures)
    use: I18n = Field(default_factory=I18n)  # from the translation files
    avoid: I18n = Field(default_factory=I18n)
    needs_confirmation: bool = False
    validated: bool = False  # computed from the trial files: some player confirmed it
    sources: list[Source] = Field(default_factory=list)


class TrialResult(Strict):
    """What one player found when trying one fingering."""

    fingering: FingeringId
    date: datetime.date | None = None
    validated: bool = True  # the player confirmed that the fingering works
    level: Level | None = None  # how demanding it is for this player
    cents: float | None = None  # measured intonation against the file's tuning (+ sharp, - flat)
    note: str = ""


class TrialFile(Strict):
    """Everything one player tried on one instrument (data/<family>/trials/<player>-<instrument>.yaml)."""

    player: str
    instrument: str  # for example "tenor"
    tuning: str = ""  # for example "A=440"
    results: list[TrialResult]


class FingeringFile(Strict):
    instrument_family: str
    fingerings: list[Fingering]


_PITCH_RE = re.compile(r"^([A-G])(#|b)?(-?\d)$")


def parse_pitch(pitch: str) -> tuple[str, str, int]:
    """Split a pitch such as ``Bb4`` into (letter, accidental, octave)."""
    m = _PITCH_RE.match(pitch)
    if not m:
        raise ValueError(f"invalid pitch: {pitch!r}")
    return m.group(1), m.group(2) or "", int(m.group(3))
