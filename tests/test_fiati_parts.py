import pytest
from fastapi.testclient import TestClient
from music21 import converter, instrument, note, stream

from windfingerflow.annotate import annotate
from windfingerflow.database import load_database
from windfingerflow.fiati import FONTS_DIR, KEY_GLYPHS, SAX_CHART, diagram_text
from windfingerflow.render import render_pdf
from windfingerflow.score import extract_line
from windfingerflow.score_parts import default_part, list_parts
from windfingerflow.web import app as webapp


def test_every_catalogue_key_has_a_glyph():
    db = load_database()
    assert set(db.keys) <= set(KEY_GLYPHS)


def test_diagram_text_starts_with_chart_and_overlays_keys():
    text = diagram_text(["lh.b", "lh.a", "lh.octave"])
    assert text[0] == chr(SAX_CHART)
    assert {ord(c) for c in text[1:]} == {KEY_GLYPHS[k] for k in ("lh.b", "lh.a", "lh.octave")}


def test_font_is_bundled_with_its_license():
    assert (FONTS_DIR / "fiati-regular.ttf").is_file()
    assert (FONTS_DIR / "OFL.txt").is_file()


@pytest.mark.parametrize("style,words", [("text", 4), ("diagram", 4), ("both", 8)])
def test_annotation_styles(tmp_path, style, words):
    score = converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4")
    events = extract_line(score)
    db = load_database()
    chosen = [db.fingerings["fs.alt" if e.pitch == "F#4" else "bb.side"] for e in events]
    assert annotate(events, chosen, style=style) == 4
    out = tmp_path / "o.musicxml"
    score.write("musicxml", fp=str(out))
    xml = out.read_text(encoding="utf-8")
    assert xml.count("<words") == words
    assert ("Fiati" in xml) == (style != "text")
    render_pdf(out, tmp_path / "o.pdf")


def two_part_score():
    score = stream.Score()
    for inst, pitches in ((instrument.Piano(), []), (instrument.AltoSaxophone(), ["B4", "C5"])):
        part = stream.Part()
        part.insert(0, inst)
        for p in pitches:
            part.append(note.Note(p))
        score.insert(0, part)
    return score


def test_list_parts_prefers_the_sax_part():
    parts = list_parts(two_part_score())
    assert [p.is_sax for p in parts] == [False, True]
    assert default_part(parts) == 1


def test_parts_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path / "w")
    p = tmp_path / "s.musicxml"
    two_part_score().write("musicxml", fp=str(p))
    client = TestClient(webapp.app)
    r = client.post("/parts", files={"file": ("s.musicxml", p.read_bytes())})
    assert r.status_code == 200 and "<select" in r.text and "selected" in r.text
    bad = client.post("/parts", files={"file": ("s.exe", b"x")})
    assert "Unsupported" in bad.text
