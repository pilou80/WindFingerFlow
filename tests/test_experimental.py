from windfingerflow.chooser import candidates
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.profile import LEVEL_ORDER, Profile


def ids(db, profile, pitch="Bb4"):
    return {f.id for f in candidates(db, pitch, profile)}


def test_experimental_is_above_expert():
    assert LEVEL_ORDER[Level.EXPERIMENTAL] > LEVEL_ORDER[Level.EXPERT]


def test_one_and_one_bb_is_advanced():
    db = load_database()
    assert db.fingerings["bb.one_one"].level == Level.ADVANCED
    assert "bb.one_one" not in ids(db, Profile(level=Level.BEGINNER))
    for level in (Level.ADVANCED, Level.EXPERT, Level.EXPERIMENTAL):
        assert "bb.one_one" in ids(db, Profile(level=level)), level
