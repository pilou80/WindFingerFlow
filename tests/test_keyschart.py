import re

from fastapi.testclient import TestClient

from windfingerflow.database import load_database
from windfingerflow.fiati import diagram_markup
from windfingerflow.keyschart import key_lines, keys_svg_pages
from windfingerflow.web import app as webapp


def test_every_catalogue_key_has_its_own_box_with_names():
    db = load_database()
    text = "".join(keys_svg_pages(db, lang="fr"))
    for key in db.keys.values():
        assert f">{key.id}<" in text
        assert key.name.en in text and key.name.fr in text.replace("&apos;", "'")


def test_each_diagram_shows_only_its_key():
    db = load_database()
    text = "".join(keys_svg_pages(db))
    for key in db.keys.values():
        assert text.count(diagram_markup([key.id])) == 1, key.id


def test_finger_group_and_confirmation_flag_are_shown():
    db = load_database()
    key = db.keys["rh.low_c"]
    assert any("R4" in t for style, t in key_lines(key, "en") if style == "info")
    assert "flag" not in dict(key_lines(key, "en"))
    flagged = key.model_copy(update={"needs_confirmation": True})  # no catalogue key is flagged now
    assert dict(key_lines(flagged, "en")).get("flag") == "! to confirm"
    assert dict(key_lines(flagged, "fr")).get("flag") == "! à confirmer"


def test_pages_fit_and_are_watermarked():
    pages = keys_svg_pages(load_database(), watermark="WindFingerFlow keys")
    assert 1 <= len(pages) <= 4 and all("WindFingerFlow keys" in p for p in pages)
    assert all(re.search(r'viewBox="0 0 1123 794"', p) for p in pages)


def test_keys_page_and_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path / "w")
    client = TestClient(webapp.app)
    assert client.get("/keys").status_code == 200
    r = client.post("/keys", data={"lang": "fr"})
    assert "<iframe" in r.text
    job = r.text.split("/download/")[1].split("/")[0]
    pdf = client.get(f"/download/{job}/keys")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    svg = client.get(f"/preview/{job}/1").text
    assert "keys" in svg and "lang=fr" in svg
    assert "err" in client.post("/keys", data={"lang": "xx"}).text


def test_french_page_has_french_name_in_bold():
    from windfingerflow.database import load_database
    from windfingerflow.keyschart import key_lines

    key = next(k for k in load_database().keys.values() if k.name.fr and k.name.fr != k.name.en)
    fr = dict(key_lines(key, "fr"))
    assert fr["name"] == key.name.fr and fr["name2"] == key.name.en
    en = dict(key_lines(key, "en"))
    assert en["name"] == key.name.en and en["name2"] == key.name.fr
