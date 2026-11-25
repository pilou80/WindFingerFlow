"""User profile: what the player can and wants to play."""

from __future__ import annotations

from dataclasses import dataclass, field

from windfingerflow.models import Finger, Level

LEVEL_ORDER = {Level.BEGINNER: 0, Level.ADVANCED: 1, Level.EXPERT: 2}


@dataclass
class Profile:
    level: Level = Level.BEGINNER
    excluded_fingerings: set[str] = field(default_factory=set)
    unavailable_fingers: set[Finger] = field(default_factory=set)
    limited_fingers: set[Finger] = field(default_factory=set)
