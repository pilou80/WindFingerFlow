from music21 import converter, instrument, key, note, stream

from windfingerflow.pipeline import run
from windfingerflow.score import extract_line, load_score


def alto_part_file(tmp_path):
    part = stream.Part()
    part.insert(0, instrument.AltoSaxophone())
    part.insert(0, key.KeySignature(2))  # written key: D major
    for p in ("B5", "C#6", "C6"):
        part.append(note.Note(p, quarterLength=1))
    score = stream.Score()
    score.insert(0, part)
    path = tmp_path / "alto.musicxml"
    score.write("musicxml", fp=str(path))
    return path


def test_displayed_notes_are_transposed_for_the_chosen_sax(tmp_path):
    src = alto_part_file(tmp_path)
    out = tmp_path / "out.musicxml"
    result = run(src, sax="tenor", lang="fr", musicxml_out=out)
    written = [e.midi for e in result.events]
    shown = converter.parse(str(out))
    notes = [n.pitch.midi for n in shown.recurse().notes]
    assert notes == written  # the displayed notes are the written tenor notes
    assert [e.pitch for e in result.events] == ["E6", "F#6", "F6"]
    inst = shown.parts[0].getInstrument(returnDefault=True)
    assert isinstance(inst, instrument.TenorSaxophone)
    assert "ténor" in (shown.parts[0].partName or "").lower()
    # the sounding pitch is unchanged: tenor sounds M9 below its written notes
    sounding = [n.pitch.midi - 14 for n in shown.recurse().notes]
    original = [n.pitch.midi - 9 for n in load_score(src).recurse().notes]
    assert sounding == original


def test_keep_as_written_leaves_the_part_alone(tmp_path):
    src = alto_part_file(tmp_path)
    out = tmp_path / "out.musicxml"
    run(src, sax=None, musicxml_out=out)
    shown = converter.parse(str(out))
    assert isinstance(shown.parts[0].getInstrument(returnDefault=True), instrument.AltoSaxophone)
    assert [n.pitch.nameWithOctave for n in shown.recurse().notes][:2] == ["B5", "C#6"]
    assert [e.pitch for e in extract_line(load_score(src))][:1] == ["B5"]
