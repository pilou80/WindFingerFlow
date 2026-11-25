"""Choose a fingering sequence by dynamic programming (Viterbi)."""

from __future__ import annotations

from dataclasses import dataclass

from windfingerflow.database import Database
from windfingerflow.models import Category, Fingering, Intonation
from windfingerflow.profile import LEVEL_ORDER, Profile

ALTERNATE_COST = 0.2  # prefer the standard fingering unless transitions say otherwise
KEY_CHANGE_COST = 1.0  # each key pressed or released
SLIDE_COST = 1.0  # a finger that stays down but changes key(s)
BAD_INTONATION_COST = 0.5
FAST_NOTE = 1.0  # notes shorter than this (quarter lengths) count as "fast"
FAST_INTONATION_FACTOR = 0.2


@dataclass
class Step:
    pitch: str
    duration: float


def candidates(db: Database, pitch: str, profile: Profile) -> list[Fingering]:
    out = []
    for f in db.candidates(pitch):
        if f.id in profile.excluded_fingerings:
            continue
        if LEVEL_ORDER[f.level] > LEVEL_ORDER[profile.level]:
            continue
        if db.fingers_for(f) & profile.unavailable_fingers:
            continue
        out.append(f)
    return sorted(out, key=lambda f: f.id)


def unary_cost(db: Database, f: Fingering, duration: float, profile: Profile) -> float:
    cost = 0.0 if f.category == Category.STANDARD else ALTERNATE_COST
    if f.intonation in (Intonation.SHARP, Intonation.FLAT):
        cost += BAD_INTONATION_COST * (FAST_INTONATION_FACTOR if duration < FAST_NOTE else 1.0)
    cost += 0.5 * len(db.fingers_for(f) & profile.limited_fingers)
    return cost


def _keys_by_finger(db: Database, f: Fingering) -> dict:
    by_finger: dict = {}
    for k in f.keys:
        by_finger.setdefault(db.keys[k].finger, set()).add(k)
    return by_finger


def transition_cost(db: Database, a: Fingering, b: Fingering) -> float:
    cost = KEY_CHANGE_COST * len(set(a.keys) ^ set(b.keys))
    fa, fb = _keys_by_finger(db, a), _keys_by_finger(db, b)
    for finger in fa.keys() & fb.keys():
        if fa[finger] != fb[finger]:
            cost += SLIDE_COST
    return cost


def choose(
    db: Database, steps: list[Step], profile: Profile | None = None
) -> list[Fingering | None]:
    """Cheapest fingering per step; ``None`` where no fingering is available.

    A step without candidates breaks the chain: the next note starts fresh.
    """
    profile = profile or Profile()
    result: list[Fingering | None] = [None] * len(steps)
    i = 0
    while i < len(steps):
        cands = candidates(db, steps[i].pitch, profile)
        if not cands:
            i += 1
            continue
        # run of consecutive steps that have candidates
        run = []
        j = i
        while j < len(steps):
            c = candidates(db, steps[j].pitch, profile)
            if not c:
                break
            run.append(c)
            j += 1
        _solve_run(db, steps[i:j], run, profile, result, i)
        i = j
    return result


def _solve_run(db, steps, run, profile, result, offset) -> None:
    cost = [[unary_cost(db, f, steps[0].duration, profile) for f in run[0]]]
    back: list[list[int]] = [[-1] * len(run[0])]
    for n in range(1, len(run)):
        row, brow = [], []
        for f in run[n]:
            options = [
                cost[n - 1][p] + transition_cost(db, prev, f) for p, prev in enumerate(run[n - 1])
            ]
            best = min(range(len(options)), key=options.__getitem__)
            row.append(options[best] + unary_cost(db, f, steps[n].duration, profile))
            brow.append(best)
        cost.append(row)
        back.append(brow)
    k = min(range(len(cost[-1])), key=cost[-1].__getitem__)
    for n in range(len(run) - 1, -1, -1):
        result[offset + n] = run[n][k]
        k = back[n][k]
