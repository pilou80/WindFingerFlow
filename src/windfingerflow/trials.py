"""Merge the players' trial files into the fingering data.

The fingering files hold the reference data only. What players found (validation, difficulty, measured
intonation) lives in ``data/<family>/trials/*.yaml``, one file per player and instrument, so several players
and instruments can accumulate their own results.
"""

from __future__ import annotations

from windfingerflow.models import LEVEL_RANK, Fingering, Intonation, Level, TrialFile

IN_TUNE_CENTS = 10  # within +/- this many cents the fingering counts as in tune


def intonation_for(cents: float) -> Intonation:
    if cents > IN_TUNE_CENTS:
        return Intonation.SHARP
    if cents < -IN_TUNE_CENTS:
        return Intonation.FLAT
    return Intonation.IN_TUNE


def apply_trials(fingering: Fingering, trials: list[TrialFile]) -> Fingering:
    """The fingering with ``validated``, ``level``, ``cents`` and ``intonation`` taken from the trials."""
    results = [r for t in trials for r in t.results if r.fingering == fingering.id]
    if not results:
        return fingering
    update: dict = {"validated": any(r.validated for r in results)}
    levels: list[Level] = [r.level for r in results if r.level is not None]
    if levels:  # several players: show the hardest level anyone reported
        update["level"] = max(levels, key=LEVEL_RANK.get)
    measures = [r.cents for r in results if r.cents is not None]
    if measures:
        cents = round(sum(measures) / len(measures), 1)
        update["cents"] = cents
        update["intonation"] = intonation_for(cents)
    return fingering.model_copy(update=update)
