from windfingerflow.database import load_database
from windfingerflow.models import Level


def test_front_f_and_fork_f_sharp_stay_advanced_and_are_marked_demanding():
    """pilou can play them at the advanced level, but they take effort (2026-11-26)."""
    db = load_database()
    for fid in ("f6.front", "fs6.fork"):
        f = db.fingerings[fid]
        assert f.level == Level.ADVANCED and "demanding" in f.avoid.en, fid
