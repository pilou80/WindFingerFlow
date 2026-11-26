from fastapi.testclient import TestClient
from music21 import converter

from windfingerflow import __version__
from windfingerflow.buildinfo import MAX_WATERMARK_CHARS, add_watermark, git_sha, watermark_text
from windfingerflow.chart import chart_svg_pages
from windfingerflow.database import load_database
from windfingerflow.pipeline import run
from windfingerflow.web import app as webapp


def test_sha_comes_from_the_build_environment(monkeypatch):
    git_sha.cache_clear()
    monkeypatch.setenv("WFF_GIT_SHA", "abc1234")
    assert git_sha() == "abc1234"
    git_sha.cache_clear()


def test_watermark_text_has_name_version_sha_and_parameters(monkeypatch):
    git_sha.cache_clear()
    monkeypatch.setenv("WFF_GIT_SHA", "abc1234")
    text = watermark_text("score", part=0, sax="alto", all_notes=True, appendix=False, exclude="")
    assert text == f"WindFingerFlow {__version__} (abc1234) - score - part=0 sax=alto all_notes"
    assert len(watermark_text("x", note="y" * 500)) <= MAX_WATERMARK_CHARS
    git_sha.cache_clear()


def test_add_watermark_handles_both_kinds_of_root_and_escapes():
    fixed = '<svg width="800px" height="600px"><g/></svg>'
    boxed = '<svg viewBox="0 0 1000 500"><g/></svg>'
    for svg in (fixed, boxed):
        out = add_watermark(svg, "a <b> & c")
        assert out.endswith("</text></svg>") and "a &lt;b&gt; &amp; c" in out and "#999" in out
    assert add_watermark("<p>not svg</p>", "x") == "<p>not svg</p>"
    assert add_watermark(fixed, "") == fixed


def test_chart_pages_carry_the_watermark():
    pages = chart_svg_pages(load_database(), watermark="WindFingerFlow test")
    assert all("WindFingerFlow test" in p for p in pages)
    assert all("WindFingerFlow" not in p for p in chart_svg_pages(load_database()))


def test_score_run_describes_its_parameters(tmp_path):
    xml = tmp_path / "in.musicxml"
    converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4").write("musicxml", fp=str(xml))
    result = run(xml, pdf_out=tmp_path / "o.pdf", appendix=True, style="diagram", lang="fr")
    assert "WindFingerFlow" in result.watermark and "style=diagram" in result.watermark
    assert "appendix" in result.watermark and "lang=fr" in result.watermark


def test_web_previews_show_the_parameters(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "WORKDIR", tmp_path / "w")
    xml = tmp_path / "in.musicxml"
    converter.parse("tinyNotation: 4/4 f#4 b-4").write("musicxml", fp=str(xml))
    client = TestClient(webapp.app)
    r = client.post(
        "/process",
        files={"file": ("a.musicxml", xml.read_bytes())},
        data={"level": "advanced", "style": "diagram"},
    )
    job = r.text.split("/preview/")[1].split("/")[0]
    svg = client.get(f"/preview/{job}/1").text
    assert "WindFingerFlow" in svg and "level=advanced" in svg and "style=diagram" in svg

    r = client.post("/chart", data={"level": "advanced", "alternates": "true", "naming": "solfege"})
    job = r.text.split("/preview/")[1].split("/")[0]
    svg = client.get(f"/preview/{job}/1").text
    assert "chart" in svg and "naming=solfege" in svg and "alternates" in svg
