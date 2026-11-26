from windfingerflow.database import load_database


def keys(db, fid):
    return set(db.fingerings[fid].keys)


def test_bb_fingerings_and_the_a_key():
    """Corrected with the saxophonist (2026-11-26).

    The normal B flat (bis) has no A key. The side B flat does: B key, A key and the side Bb key.
    """
    db = load_database()
    assert keys(db, "bb.bis") == {"lh.b", "lh.bis"}
    assert keys(db, "bb.side") == {"lh.b", "lh.a", "rh.side_bb"}
    assert "lh.a" not in keys(db, "bb.bis")


def test_one_and_one_bb_has_no_a_key_for_now():
    """Not validated: it stays experimental, and was changed with the bis fingering."""
    db = load_database()
    assert keys(db, "bb.one_one") == {"lh.b", "rh.f"}
