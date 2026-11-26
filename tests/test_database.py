import pytest

from windfingerflow.database import load_database
from windfingerflow.models import Finger


@pytest.fixture(scope="module")
def db():
    return load_database("saxophone")


def test_every_key_has_english_and_french_names(db):
    assert all(k.name.en and k.name.fr for k in db.keys.values())


def test_bb_candidates(db):
    ids = {f.id for f in db.candidates("Bb4")}
    assert ids == {"bb.bis", "bb.one_one", "bb.side"}


def test_derived_fingers(db):
    assert db.fingers_for(db.fingerings["bb.bis"]) == {Finger.L1}  # B + bis key, both by the index
    assert db.fingers_for(db.fingerings["bb.side"]) == {Finger.L1, Finger.L2, Finger.R1}
    assert db.fingers_for(db.fingerings["fs.std"]) == {
        Finger.L1,
        Finger.L2,
        Finger.L3,
        Finger.R2,
    }


def test_alternate_fs_is_confirmed_and_offered_by_default(db):
    assert not db.keys["rh.alt_fs"].needs_confirmation
    assert not db.fingerings["fs.alt"].needs_confirmation


def test_unavailable_finger_excludes_standard_fs(db):
    """Design notes §12: with R2 unavailable, standard F# goes, alternate F# stays."""
    unavailable = {Finger.R2}
    playable = {f.id for f in db.candidates("F#4") if not (db.fingers_for(f) & unavailable)}
    assert playable == {"fs.alt"}
