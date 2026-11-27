import pytest
from pypdf import PdfReader

from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.profile import Profile
from windfingerflow.render import render_pdf


@pytest.fixture(scope="module")
def db():
    return load_database("saxophone")


def ids(chosen):
    return [f.id if f else None for f in chosen]


def test_side_c_chosen_in_fast_passage_for_advanced(db):
    steps = [Step(p, 0.5) for p in ("B4", "C5", "B4")]
    assert ids(choose(db, steps, Profile(level=Level.ADVANCED))) == ["b.std", "c.side", "b.std"]


def test_side_c_hidden_from_beginners(db):
    steps = [Step(p, 0.5) for p in ("B4", "C5", "B4")]
    assert ids(choose(db, steps)) == ["b.std", "c.std", "b.std"]


def test_render_pdf(tmp_path):
    from music21 import converter

    xml = tmp_path / "in.musicxml"
    converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4").write("musicxml", fp=str(xml))
    out = tmp_path / "out.pdf"
    assert render_pdf(xml, out) >= 1
    assert len(PdfReader(str(out)).pages) >= 1


def test_text_annotations_are_slanted_but_diagrams_are_not():
    from windfingerflow.render import _slant_annotations

    svg = (
        '<g id="a" class="dir"><text x="10" y="20" font-size="0px"><tspan font-size="405px">Fa avant</tspan></text></g>'
        '<g id="b" class="dir"><text x="30" y="40" font-size="0px"><tspan font-size="900px" font-family="Fiati">X</tspan></text></g>'
    )
    out = _slant_annotations(svg)
    assert 'transform="rotate(-45 10 20)"' in out
    assert "rotate" not in out.split("Fiati")[0].split("Fa avant</tspan></text></g>")[1]
