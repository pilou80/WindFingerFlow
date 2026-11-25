from fastapi.testclient import TestClient
from music21 import converter

from windfingerflow.web import app as webapp


def test_preview_is_served_safely(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path / "w")
    xml = tmp_path / "in.musicxml"
    converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4").write("musicxml", fp=str(xml))
    client = TestClient(webapp.app)
    r = client.post(
        "/process",
        files={"file": ("a.musicxml", xml.read_bytes())},
        data={"style": "diagram"},
    )
    assert "<iframe" in r.text and "<table" not in r.text
    job = r.text.split("/preview/")[1].split("/")[0]
    svg = client.get(f"/preview/{job}/1")
    assert svg.status_code == 200 and svg.headers["content-type"].startswith("image/svg+xml")
    assert "default-src 'none'" in svg.headers["content-security-policy"]
    assert svg.text.lstrip().startswith("<svg") and "viewBox" in svg.text[:300]
    assert "Fiati" in svg.text and "<script" not in svg.text
    assert client.get("/fonts/fiati-regular.ttf").status_code == 200
    assert client.get(f"/preview/{job}/99").status_code == 404
    assert client.get("/preview/not-a-job/1").status_code == 404
