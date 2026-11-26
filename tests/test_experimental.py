from windfingerflow.chooser import Step, candidates, choose
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.profile import LEVEL_ORDER, Profile


def ids(db, profile, pitch="Bb4"):
    return {f.id for f in candidates(db, pitch, profile)}


def test_experimental_is_above_expert():
    assert LEVEL_ORDER[Level.EXPERIMENTAL] > LEVEL_ORDER[Level.EXPERT]


def test_one_and_one_bb_is_experimental_only():
    db = load_database()
    assert db.fingerings["bb.one_one"].level == Level.EXPERIMENTAL
    for level in (Level.BEGINNER, Level.ADVANCED, Level.EXPERT):
        assert "bb.one_one" not in ids(db, Profile(level=level)), level
    assert "bb.one_one" in ids(db, Profile(level=Level.EXPERIMENTAL))


def test_scores_no_longer_get_one_and_one_unless_experimental():
    db = load_database()
    steps = [Step(p, 0.5) for p in ("F#4", "Bb4", "F#4", "Bb4", "F#4")]
    for level in (Level.BEGINNER, Level.ADVANCED, Level.EXPERT):
        chosen = choose(db, steps, Profile(level=level))
        assert all(f.id != "bb.one_one" for f in chosen if f), level
