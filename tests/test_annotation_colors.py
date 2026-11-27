from music21 import expressions, instrument, note, stream

from windfingerflow.annotate import PALETTE, annotate
from windfingerflow.database import load_database
from windfingerflow.score import extract_line


def test_each_distinct_fingering_gets_its_own_colour():
    db = load_database()
    part = stream.Part()
    part.insert(0, instrument.AltoSaxophone())
    measure = stream.Measure()
    for p in ("F#5", "C5", "F#5", "C5"):  # fs.alt twice, c.side twice, alternating
        measure.append(note.Note(p, quarterLength=1))
    part.append(measure)
    score = stream.Score()
    score.insert(0, part)
    events = extract_line(score)
    chosen = [db.fingerings["fs.alt"], db.fingerings["c.side"]] * 2
    assert annotate(events, chosen, "en") == 4
    colors = [e.element.style.color for e in events]
    assert colors[0] == colors[2] and colors[1] == colors[3] and colors[0] != colors[1]
    assert set(colors) <= set(PALETTE)
    words = list(part.recurse().getElementsByClass(expressions.TextExpression))
    assert [w.style.color for w in words] == colors
