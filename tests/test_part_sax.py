from fastapi.testclient import TestClient
from music21 import instrument, note, stream

from windfingerflow.score_parts import list_parts
from windfingerflow.web import app as webapp


def alto_file(tmp_path):
    part = stream.Part()
    part.insert(0, instrument.AltoSaxophone())
    part.append(note.Note("B5", quarterLength=1))
    score = stream.Score()
    score.insert(0, part)
    path = tmp_path / "alto.musicxml"
    score.write("musicxml", fp=str(path))
    return path


def test_parts_know_their_own_sax(tmp_path):
    from windfingerflow.score import load_score

    info = list_parts(load_score(alto_file(tmp_path)))
    assert info[0].is_sax and info[0].sax == "alto"
    flute = stream.Part()
    flute.insert(0, instrument.Flute())
    flute.append(note.Note("C5"))
    assert list_parts(stream.Score([flute]))[0].sax == ""


def test_part_selector_carries_the_sax_kind_and_the_page_rebuilds_the_list(tmp_path):
    client = TestClient(webapp.app)
    path = alto_file(tmp_path)
    with path.open("rb") as fh:
        html = client.post("/parts", files={"file": ("alto.musicxml", fh)}).text
    assert 'data-sax="alto"' in html
    page = client.get("/?ui=fr").text
    assert 'id="sax-i18n"' in page and "transposer" in page
