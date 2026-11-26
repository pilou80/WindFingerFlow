from windfingerflow.database import load_database


def keys(db, fid):
    return set(db.fingerings[fid].keys)


def test_low_c_key_is_pressed_for_low_c_and_the_three_notes_below_c_sharp():
    """Validated by the saxophonist (2026-11-26): the low C key is used for low Bb, B, C# and C."""
    db = load_database()
    for fid in ("bb.low", "b.low", "cs.low", "c.low"):
        assert "rh.low_c" in keys(db, fid), fid
    # each of the three keeps its own pinky key as well
    assert "lh.low_bb" in keys(db, "bb.low")
    assert "lh.low_b" in keys(db, "b.low")
    assert "lh.low_cs" in keys(db, "cs.low")
    # D and above do not use it
    assert "rh.low_c" not in keys(db, "d.std")


def test_low_c_key_is_confirmed():
    db = load_database()
    assert not db.keys["rh.low_c"].needs_confirmation
    assert all(
        not f.needs_confirmation
        for fid, f in db.fingerings.items()
        if fid != "d.long" and not fid.endswith(("6.alt", "7.alt"))
    )
