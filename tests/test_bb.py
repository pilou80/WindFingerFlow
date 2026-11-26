from windfingerflow.database import load_database


def test_no_normal_or_alternate_bb_presses_the_a_key():
    """The A key (left middle finger) makes an A; a B flat is the B key plus something else."""
    db = load_database()
    assert set(db.fingerings["bb.bis"].keys) == {"lh.b", "lh.bis"}
    assert set(db.fingerings["bb.one_one"].keys) == {"lh.b", "rh.f"}
    assert set(db.fingerings["bb.side"].keys) == {"lh.b", "rh.side_bb"}
    for fid in ("bb.bis", "bb.one_one", "bb.side"):
        assert "lh.a" not in db.fingerings[fid].keys, fid
