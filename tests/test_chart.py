from fastapi.testclient import TestClient

from windfingerflow.chart import chart_cells, chart_svg_pages, note_label
from windfingerflow.database import load_database
from windfingerflow.fiati import diagram_text
from windfingerflow.models import Level
from windfingerflow.profile import Profile
from windfingerflow.web import app as webapp


def test_labels():
    assert note_label("C", "♯", 4, "letters") == "C♯4"
    assert note_label("B", "♭", 4, "solfege") == "Si♭4"


def test_cells_cover_four_accidentals_and_the_range():
    rows = chart_cells()
    assert rows[0][:2] == ("A", 3)  # A#3 is the written low Bb3, A##3 is B3
    assert [c is not None for c in rows[0][2]] == [False, False, True, True]
    assert all(len(cells) == 4 for _, _, cells in rows)
    labels = {(letter, octave) for letter, octave, _ in rows}
    assert ("C", 4) in labels and ("A", 5) in labels


def test_enharmonic_spellings_share_a_diagram():
    pages = "".join(chart_svg_pages(load_database()))
    cs = diagram_text(load_database().fingerings["cs.low"].keys)
    # C#4 and Db4 are the same pitch, so the same glyph string appears at least twice
    assert pages.count(cs) >= 2


def test_double_sharp_is_present_and_resolves():
    pages = "".join(chart_svg_pages(load_database(), lang="fr", naming="solfege"))
    assert "Do♯♯4" in pages and "Mi♭4" in pages


def test_alternates_are_opt_in_and_named():
    db = load_database()
    without = "".join(chart_svg_pages(db, Profile(level=Level.ADVANCED)))
    with_alt = "".join(
        chart_svg_pages(db, Profile(level=Level.ADVANCED), alternates=True, lang="fr")
    )
    assert "Sib 1+1" not in without and "Sib 1+1" in with_alt


def test_responsive_pages_load_the_font():
    page = chart_svg_pages(load_database(), responsive=True)[0]
    assert "@font-face" in page and 'width="794"' not in page


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


def test_ledger_lines():
    from windfingerflow.chart import ledger_positions

    assert ledger_positions(30) == [] and ledger_positions(39) == []
    assert ledger_positions(27) == [28] and ledger_positions(26) == [28, 26]
    assert ledger_positions(40) == [40] and ledger_positions(43) == [40, 42]


def test_every_cell_is_drawn_on_a_staff():
    pages = "".join(chart_svg_pages(load_database()))
    assert pages.count("\ue050") == sum(1 for _, _, cells in chart_cells() for c in cells if c)
    for glyph in ("\ue260", "\ue262", "\ue263", "\ue0a2"):
        assert glyph in pages


def test_font_route_is_whitelisted(tmp_path, monkeypatch):
    client = TestClient(webapp.app)
    assert client.get("/fonts/Bravura.otf").status_code == 200
    assert client.get("/fonts/..%2Fsecret").status_code == 404
    assert client.get("/fonts/other.ttf").status_code == 404
