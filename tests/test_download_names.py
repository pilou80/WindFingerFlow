from fastapi.testclient import TestClient

from windfingerflow.buildinfo import stamp_musicxml
from windfingerflow.web import app as webapp


def test_stamp_adds_identification_field_and_credit(tmp_path):
    xml = tmp_path / "a.musicxml"
    xml.write_text(
        "<score-partwise><identification><encoding><software>x</software></encoding></identification>"
        "<part-list/></score-partwise>",
        encoding="utf-8",
    )
    stamp_musicxml(xml, "WindFingerFlow 0.1 (abc1234) - score a<b")
    out = xml.read_text(encoding="utf-8")
    assert (
        'miscellaneous-field name="WindFingerFlow">WindFingerFlow 0.1 (abc1234) - score a&lt;b<'
        in out
    )
    assert '<credit page="1">' in out and out.index("<credit") < out.index("<part-list")


def test_stamp_without_identification(tmp_path):
    xml = tmp_path / "b.musicxml"
    xml.write_text("<score-partwise><part-list/></score-partwise>", encoding="utf-8")
    stamp_musicxml(xml, "wm")
    out = xml.read_text(encoding="utf-8")
    assert out.index("<identification>") < out.index("<credit") < out.index("<part-list")


def test_downloads_keep_the_original_name(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path)
    job = "0" * 32
    folder = tmp_path / job
    folder.mkdir()
    (folder / "annotated.pdf").write_bytes(b"%PDF")
    (folder / "annotated.musicxml").write_text("<x/>", encoding="utf-8")
    (folder / "name.txt").write_text("Darude/Sandstorm: alto", encoding="utf-8")
    client = TestClient(webapp.app)
    from urllib.parse import unquote

    pdf = client.get(f"/download/{job}/pdf")
    assert "Darude_Sandstorm_ alto - WindFingerFlow annotated.pdf" in unquote(
        pdf.headers["content-disposition"]
    )
    xml = client.get(f"/download/{job}/musicxml")
    assert "WindFingerFlow annotated.musicxml" in unquote(xml.headers["content-disposition"])
