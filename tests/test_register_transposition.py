import pytest
from music21 import instrument, note, stream

from windfingerflow.chooser import Step, choose, effective_keys
from windfingerflow.database import load_database
from windfingerflow.instrument import midi_to_name, name_to_midi, needs_octave_key
from windfingerflow.models import Finger
from windfingerflow.profile import Profile
from windfingerflow.score import extract_line, range_warnings


@pytest.fixture(scope="module")
def db():
    return load_database("saxophone")


def make_part(inst, *pitches):
    part = stream.Part()
    part.insert(0, inst)
    for p in pitches:
        part.append(note.Note(p, quarterLength=1))
    score = stream.Score()
    score.insert(0, part)
    return score


def test_pitch_names_roundtrip():
    assert midi_to_name(name_to_midi("Bb4")) == "Bb4"
    assert midi_to_name(name_to_midi("A#4")) == "Bb4"
    assert midi_to_name(name_to_midi("Cb5")) == "B4"


def test_octave_key_register():
    assert not needs_octave_key("C#5")
    assert needs_octave_key("D5")
    assert needs_octave_key("C#6")
    assert not needs_octave_key("F4")


def test_flute_part_to_alto_and_tenor():
    score = make_part(instrument.Flute(), "C5")
    assert [e.pitch for e in extract_line(score, target_sax="alto")] == ["A5"]
    assert [e.pitch for e in extract_line(score, target_sax="tenor")] == ["D6"]


def test_sax_part_kept_as_written():
    score = make_part(instrument.AltoSaxophone(), "B4")
    assert [e.pitch for e in extract_line(score)] == ["B4"]


def test_range_warning():
    score = make_part(instrument.Flute(), "C7")
    assert range_warnings(extract_line(score))


def test_every_chromatic_pitch_has_a_fingering(db):
    for midi in range(name_to_midi("Bb3"), name_to_midi("C#6") + 1):
        assert db.candidates(midi_to_name(midi)), midi_to_name(midi)


def test_octave_key_is_added(db):
    f = db.fingerings["g.std"]
    assert "lh.octave" not in effective_keys(f, "G4")
    assert "lh.octave" in effective_keys(f, "G5")


def test_unavailable_thumb_blocks_upper_register(db):
    chosen = choose(db, [Step("G5", 1.0)], Profile(unavailable_fingers={Finger.LT}))
    assert chosen == [None]
