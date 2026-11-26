from music21 import converter

from windfingerflow.annotate import annotate
from windfingerflow.database import load_database
from windfingerflow.score import extract_line


def test_annotations_reach_the_musicxml(tmp_path):
    score = converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4")
    events = extract_line(score)
    db = load_database()
    # fixed fingerings: this test is about the output, not about what the chooser picks
    chosen = [db.fingerings["fs.alt" if e.pitch == "F#4" else "bb.side"] for e in events]
    assert annotate(events, chosen, lang="fr") == 4
    out = tmp_path / "out.musicxml"
    score.write("musicxml", fp=str(out))
    xml = out.read_text(encoding="utf-8")
    assert xml.count("<words") == 4
    assert 'placement="above"' in xml
