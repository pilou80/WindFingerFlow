from windfingerflow.chart import chart_svg_pages
from windfingerflow.chooser import Step, choose, effective_keys
from windfingerflow.database import load_database
from windfingerflow.models import Finger, Level
from windfingerflow.profile import Profile


def test_palm_keys_build_up_cumulatively():
    db = load_database()
    keys = {
        i: set(db.fingerings[i].keys)
        for i in ("d6.palm", "eb6.palm", "e6.palm", "f6.palm", "fs6.palm")
    }
    assert keys["d6.palm"] < keys["eb6.palm"] < keys["e6.palm"] < keys["f6.palm"] < keys["fs6.palm"]
    assert "rh.high_fs" in keys["fs6.palm"] and "rh.high_fs" not in keys["f6.palm"]


def test_octave_key_applies_to_the_whole_palm_register():
    db = load_database()
    assert "lh.octave" in effective_keys(db.fingerings["fs6.palm"], "F#6")
    assert "lh.octave" in effective_keys(db.fingerings["d6.palm"], "D6")


def test_whole_standard_range_is_covered_up_to_f_sharp():
    db = load_database()
    for pitch in ("D6", "Eb6", "E6", "F6", "F#6"):
        assert db.candidates(pitch), pitch
    steps = [Step(p, 1.0) for p in ("C#6", "D6", "Eb6", "E6", "F6", "F#6")]
    assert all(choose(db, steps))


def test_front_f_is_an_advanced_alternate():
    db = load_database()
    beginner = {f.id for f in db.candidates("F6")}
    assert {"f6.palm", "f6.front"} <= beginner
    chosen = choose(db, [Step("F6", 1.0)], Profile(level=Level.BEGINNER))
    assert chosen[0].id == "f6.palm"


def test_unavailable_side_finger_falls_back_to_the_fork():
    db = load_database()
    # the palm-key E needs the side E key (right index); the fork E does not
    chosen = choose(
        db, [Step("E6", 1.0)], Profile(level=Level.EXPERT, unavailable_fingers={Finger.R1})
    )
    assert chosen[0].id == "e6.fork"


def test_chart_has_no_empty_cell_any_more():
    pages = "".join(chart_svg_pages(load_database()))
    assert "no data" not in pages
