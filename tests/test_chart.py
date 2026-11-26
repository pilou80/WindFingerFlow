from fastapi.testclient import TestClient

from windfingerflow.chart import (
    PAGE_W,
    chart_svg_pages,
    ledger_positions,
    note_label,
    pitch_groups,
)
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.profile import Profile
from windfingerflow.web import app as webapp


def labels(**kw):
    pages = chart_svg_pages(load_database(), **kw)
    return pages, "".join(pages)


def test_labels():
    assert note_label("C", "♯", 4, "letters") == "C♯4"
    assert note_label("B", "♭", 4, "solfege") == "Si♭4"


def test_enharmonic_notes_are_grouped_by_pitch():
    groups = {midi: [(n, a, o) for n, a, o in sp] for midi, sp in pitch_groups()}
    assert sorted(a for _, a, _ in groups[70]) == ["♭", "♭♭", "♯"]  # A#4, Bb4, Cbb5
    assert len(groups[71]) == 3  # B4, A##4, Cb5
    assert len(groups[73]) == 3  # C#5, Db5, B##4
    assert all(len(sp) >= 1 for sp in groups.values())


def test_every_written_pitch_appears_once():
    midis = [m for m, _ in pitch_groups()]
    assert midis == sorted(set(midis)) and midis[0] == 58 and midis[-1] == 90


def test_group_label_lists_all_spellings_in_one_cell():
    import re

    _, text = labels(lang="fr", naming="solfege")
    plain = re.sub(r"<[^>]+>", "", text)  # the coloured middle note is wrapped in a tspan
    assert "La♯4 / Si♭4 / Do♭♭5" in plain
    assert "Mi♭4" in plain and "Do♯♯4" in plain


def test_one_diagram_per_group_not_per_spelling():
    db = load_database()
    from windfingerflow.fiati import diagram_text

    glyphs = diagram_text(db.fingerings["g.std"].keys)  # G4 only has one spelling group
    _, text = labels()
    assert text.count(f">{glyphs}<") == 1  # exact element: other fingerings share its prefix


def test_alternates_are_opt_in_and_named():
    db = load_database()
    without = "".join(chart_svg_pages(db, Profile(level=Level.EXPERIMENTAL)))
    with_alt = "".join(
        chart_svg_pages(db, Profile(level=Level.EXPERIMENTAL), alternates=True, lang="fr")
    )
    assert "Sib 1+1" not in without and "Sib 1+1" in with_alt


def test_responsive_pages_load_the_fonts():
    page = chart_svg_pages(load_database(), responsive=True)[0]
    assert "@font-face" in page and "Bravura" in page and f'width="{PAGE_W}"' not in page


def test_ledger_lines():
    assert ledger_positions(30) == [] and ledger_positions(39) == []
    assert ledger_positions(27) == [28] and ledger_positions(26) == [28, 26]
    assert ledger_positions(40) == [40] and ledger_positions(43) == [40, 42]


def test_every_group_is_drawn_on_a_staff():
    pages, text = labels()
    assert text.count("\ue050") == len(pitch_groups())
    for glyph in ("\ue260", "\ue262", "\ue263", "\ue264", "\ue0a2"):
        assert glyph in text
    assert len(pages) >= 2


def test_chart_page_and_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path / "w")
    client = TestClient(webapp.app)
    assert client.get("/chart").status_code == 200
    r = client.post("/chart", data={"alternates": "true", "lang": "fr", "naming": "solfege"})
    assert "<iframe" in r.text
    job = r.text.split("/download/")[1].split("/")[0]
    pdf = client.get(f"/download/{job}/chart")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.post("/chart", data={"naming": "klingon"}).text.count("err") >= 1


def test_font_route_is_whitelisted():
    client = TestClient(webapp.app)
    assert client.get("/fonts/Bravura.otf").status_code == 200
    assert client.get("/fonts/..%2Fsecret").status_code == 404
    assert client.get("/fonts/other.ttf").status_code == 404


def test_chart_is_black_and_white():
    _, text = labels()
    assert "d35400" not in text and "<tspan" not in text


def test_alternates_follow_the_standard_fingering_beside_the_staff():
    import re

    db = load_database()
    plain = "".join(chart_svg_pages(db, Profile(level=Level.ADVANCED)))
    side = "".join(chart_svg_pages(db, Profile(level=Level.ADVANCED), alternates=True))
    # a dashed separator marks where the alternates start; there is no longer a band under the staff
    assert "stroke-dasharray" not in plain and "stroke-dasharray" in side
    assert not re.search(
        r'<line x1="[\d.]+" y1="[\d.]+" x2="[\d.]+" y2="[\d.]+" stroke="#ccc"', side
    )
    assert side.count("<rect x=") == plain.count("<rect x=")
