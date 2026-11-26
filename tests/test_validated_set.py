from windfingerflow.database import load_database
from windfingerflow.models import Level


def test_what_pilou_has_validated():
    """2026-11-26: all beginner fingerings, the side C, and the front F / fork F# he can play."""
    db = load_database()
    for f in db.fingerings.values():
        if f.level == Level.BEGINNER:
            assert f.validated, f.id
    for fid in ("c.side", "f6.front", "fs6.fork"):
        assert db.fingerings[fid].validated, fid


def test_what_is_still_to_confirm():
    db = load_database()
    pending = {f.id for f in db.fingerings.values() if not f.validated}
    assert pending == {"bb.one_one", "d.long", "e6.fork"}
