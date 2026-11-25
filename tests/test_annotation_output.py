from music21 import converter

from windfingerflow.annotate import annotate
from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.profile import Profile
from windfingerflow.score import extract_line


def test_annotations_reach_the_musicxml(tmp_path):
    score = converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4")
    events = extract_line(score)
    profile = Profile(allow_unconfirmed=True)
    chosen = choose(load_database(), [Step(e.pitch, e.duration) for e in events], profile)
    assert annotate(events, chosen, lang="fr") == 4
    out = tmp_path / "out.musicxml"
    score.write("musicxml", fp=str(out))
    xml = out.read_text(encoding="utf-8")
    assert xml.count("<words") == 4
    assert 'placement="above"' in xml
