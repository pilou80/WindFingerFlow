from music21 import converter
from pypdf import PdfReader

from windfingerflow.appendix import appendix_svg_pages, collect_entries, format_bars
from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.pipeline import run
from windfingerflow.profile import Profile


def test_format_bars():
    assert format_bars([3, 4, 5, 8, 10, 11]) == "3-5, 8, 10-11"
    assert format_bars([]) == "-"


def make_xml(tmp_path):
    xml = tmp_path / "in.musicxml"
    converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4 f#4 b-4 f#4 b-4").write(
        "musicxml", fp=str(xml)
    )
    return xml


def test_entries_collect_bars(tmp_path):
    from windfingerflow.score import extract_line, load_score

    events = extract_line(load_score(make_xml(tmp_path)))
    db = load_database()
    chosen = choose(
        db,
        [Step(e.pitch, e.duration) for e in events],
        Profile(level=Level.EXPERIMENTAL, allow_unconfirmed=True),
    )
    entries = collect_entries(events, chosen)
    assert {e.fingering.id for e in entries} == {"fs.alt", "bb.one_one"}
    assert all(e.bars == [1, 2] for e in entries)


def test_appendix_svg_mentions_name_and_bars(tmp_path):
    from windfingerflow.score import extract_line, load_score

    events = extract_line(load_score(make_xml(tmp_path)))
    chosen = choose(
        load_database(),
        [Step(e.pitch, e.duration) for e in events],
        Profile(level=Level.EXPERIMENTAL),
    )
    pages = appendix_svg_pages(collect_entries(events, chosen), "fr")
    assert len(pages) == 1 and "Sib 1+1" in pages[0] and "Mesures: 1-2" in pages[0]


def test_pdf_gets_an_extra_page(tmp_path):
    xml = make_xml(tmp_path)
    plain = run(xml, pdf_out=tmp_path / "a.pdf")
    with_app = run(xml, pdf_out=tmp_path / "b.pdf", appendix=True)
    assert with_app.pages == plain.pages  # score pages unchanged
    assert (
        len(PdfReader(str(tmp_path / "b.pdf")).pages)
        == len(PdfReader(str(tmp_path / "a.pdf")).pages) + 1
    )
