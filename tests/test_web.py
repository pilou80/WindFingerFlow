import pytest
from fastapi.testclient import TestClient
from music21 import converter

from windfingerflow.web import app as webapp


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path / "work")
    return TestClient(webapp.app)


@pytest.fixture()
def xml_bytes(tmp_path):
    p = tmp_path / "in.musicxml"
    converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4").write("musicxml", fp=str(p))
    return p.read_bytes()


def test_index_in_french(client):
    r = client.get("/", headers={"accept-language": "fr-FR"})
    assert r.status_code == 200 and "Analyser" in r.text


def test_process_and_download(client, xml_bytes):
    r = client.post("/process", files={"file": ("a.musicxml", xml_bytes)}, data={"lang": "fr"})
    assert r.status_code == 200 and "/download/" in r.text and "Fa# alternatif" in r.text
    job = r.text.split("/download/")[1].split("/")[0]
    pdf = client.get(f"/download/{job}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get(f"/download/{job}/musicxml").status_code == 200


def test_rejects_bad_extension(client):
    r = client.post("/process", files={"file": ("evil.exe", b"x")})
    assert "Unsupported file type" in r.text


def test_rejects_oversize(client, monkeypatch, xml_bytes):
    monkeypatch.setattr(webapp, "MAX_UPLOAD_BYTES", 10)
    r = client.post("/process", files={"file": ("a.musicxml", xml_bytes)})
    assert "too large" in r.text


def test_garbage_file_gives_clean_error(client):
    r = client.post("/process", files={"file": ("a.musicxml", b"not xml")})
    assert "could not be read" in r.text and "Traceback" not in r.text


def test_download_rejects_path_tricks(client):
    assert client.get("/download/..%2F..%2Fetc/pdf").status_code == 404
    assert client.get("/download/" + "0" * 32 + "/pdf").status_code == 404
