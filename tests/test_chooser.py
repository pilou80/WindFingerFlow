import pytest
from music21 import converter

from windfingerflow.annotate import annotate
from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.models import Finger
from windfingerflow.profile import Profile
from windfingerflow.score import extract_line


@pytest.fixture(scope="module")
def db():
    return load_database("saxophone")


def steps(*pitches, dur=1.0):
    return [Step(p, dur) for p in pitches]


def ids(chosen):
    return [f.id if f else None for f in chosen]


def test_single_notes_pick_standard(db):
    assert ids(choose(db, steps("Bb4"))) == ["bb.bis"]
    assert ids(choose(db, steps("F#4"))) == ["fs.std"]


def test_exclusion_changes_choice(db):
    chosen = choose(db, steps("Bb4"), Profile(excluded_fingerings={"bb.bis"}))
    assert ids(chosen)[0] in {"bb.one_one", "bb.side"}


def test_unavailable_r2_forces_alternate_fs(db):
    chosen = choose(
        db, steps("F#4", "F#4"), Profile(unavailable_fingers={Finger.R2}, allow_unconfirmed=True)
    )
    assert ids(chosen) == ["fs.alt", "fs.alt"]


def test_fs_bb_fs_avoids_bis(db):
    chosen = ids(choose(db, steps("F#4", "Bb4", "F#4")))
    assert chosen[1] != "bb.bis"


def test_note_without_data_breaks_chain(db):
    assert ids(choose(db, steps("A6", "Bb4"))) == [None, "bb.bis"]


def test_tinynotation_end_to_end(db):
    score = converter.parse("tinyNotation: 4/4 f#4 b-4 f#4 b-4")
    events = extract_line(score)
    assert [e.pitch for e in events] == ["F#4", "Bb4", "F#4", "Bb4"]
    chosen = choose(db, [Step(e.pitch, e.duration) for e in events])
    assert annotate(events, chosen) >= 1
