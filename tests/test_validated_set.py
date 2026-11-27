from windfingerflow.database import load_database
from windfingerflow.models import Level


def test_what_pilou_has_validated():
    """2026-11-26: all beginner fingerings, the side C, and the front F / fork F# he can play."""
    db = load_database()
    for f in db.fingerings.values():
        if f.level == Level.BEGINNER:
            assert f.validated, f.id
    for fid in ("c.side", "f6.front", "fs6.fork", "bb.one_one", "c.a_g_gs"):
        assert db.fingerings[fid].validated, fid


def test_what_is_still_to_confirm():
    import yaml

    from windfingerflow.database import DEFAULT_DATA_DIR

    db = load_database()
    pending = {f.id for f in db.fingerings.values() if not f.validated}
    altissimo = {"g6.alt", "gs6.alt", "a6.alt", "bb6.alt", "b6.alt", "c7.alt"}
    path = DEFAULT_DATA_DIR / "saxophone" / "fingering" / "to_test.yaml"
    to_test = {f["id"] for f in yaml.safe_load(path.read_text(encoding="utf-8"))["fingerings"]}
    assert to_test and pending == {"d.long", "e6.fork"} | altissimo | to_test
