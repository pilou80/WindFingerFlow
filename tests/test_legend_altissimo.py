from windfingerflow.chart import chart_svg_pages
from windfingerflow.chooser import candidates
from windfingerflow.database import load_database
from windfingerflow.legend import COLORS, fingering_color
from windfingerflow.models import Level
from windfingerflow.profile import Profile


def test_colours_follow_level_and_validation():
    db = load_database()
    assert fingering_color(db.fingerings["bb.side"]) == COLORS["beginner"]
    assert fingering_color(db.fingerings["c.side"]) == COLORS["advanced"]
    assert fingering_color(db.fingerings["d.long"]) == COLORS["to_test"]
    assert fingering_color(db.fingerings["g6.alt"]) == COLORS["to_test"]


def test_chart_has_a_legend_with_alternates_only():
    db = load_database()
    with_alt = "".join(chart_svg_pages(db, alternates=True, lang="fr"))
    assert "à tester" in with_alt and COLORS["advanced"] in with_alt
    assert "à tester" not in "".join(chart_svg_pages(db, alternates=False, lang="fr"))


def test_altissimo_is_opt_in():
    db = load_database()
    off = Profile(level=Level.EXPERIMENTAL, allow_unconfirmed=True)
    on = Profile(level=Level.EXPERIMENTAL, allow_unconfirmed=True, allow_altissimo=True)
    assert candidates(db, "G6", off) == []
    assert [f.id for f in candidates(db, "G6", on)] == ["g6.alt"]
    plain = "".join(chart_svg_pages(db, off))
    wide = "".join(chart_svg_pages(db, on, alternates=True))
    assert len(wide) > len(plain)
