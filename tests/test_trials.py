import datetime

import pytest
import yaml

from windfingerflow.database import DEFAULT_DATA_DIR, DataError, load_database
from windfingerflow.models import Fingering, Intonation, Level, TrialFile, TrialResult
from windfingerflow.trials import apply_trials

FINGERING_DIR = DEFAULT_DATA_DIR / "saxophone" / "fingering"


def fingering(**kw):
    base = {
        "id": "x.test",
        "pitches": ["C5"],
        "keys": ["lh.b"],
        "category": "alternate",
        "level": "advanced",
    }
    return Fingering.model_validate({**base, **kw})


def trial(player, *results):
    return TrialFile(player=player, instrument="tenor", tuning="A=440", results=list(results))


def test_a_fingering_without_trials_is_unchanged():
    f = fingering()
    assert apply_trials(f, [trial("a", TrialResult(fingering="y.other"))]) == f


def test_one_trial_sets_validation_level_and_intonation():
    f = apply_trials(
        fingering(),
        [
            trial(
                "a",
                TrialResult(
                    fingering="x.test", level="expert", cents=-13, date=datetime.date(2026, 11, 27)
                ),
            )
        ],
    )
    assert (
        f.validated
        and f.level == Level.EXPERT
        and f.cents == -13
        and f.intonation == Intonation.FLAT
    )


def test_players_accumulate():
    f = apply_trials(
        fingering(),
        [
            trial("a", TrialResult(fingering="x.test", level="advanced", cents=14)),
            trial("b", TrialResult(fingering="x.test", level="expert", cents=4, validated=False)),
        ],
    )
    assert f.validated  # one player confirmed it
    assert f.level == Level.EXPERT  # the hardest level reported
    assert f.cents == 9 and f.intonation == Intonation.IN_TUNE  # mean of the measures


def test_tried_but_not_validated_stays_to_test():
    f = apply_trials(fingering(), [trial("a", TrialResult(fingering="x.test", validated=False))])
    assert not f.validated


def test_unknown_fingering_in_a_trial_file_is_an_error(tmp_path):
    import shutil

    shutil.copytree(DEFAULT_DATA_DIR / "saxophone", tmp_path / "saxophone")
    (tmp_path / "saxophone" / "trials" / "bad.yaml").write_text(
        yaml.safe_dump(
            {"player": "z", "instrument": "alto", "results": [{"fingering": "zz.nope"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(DataError, match="zz.nope"):
        load_database("saxophone", tmp_path)


def test_fingering_files_hold_reference_data_only():
    for path in FINGERING_DIR.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for field in ("validated:", "cents:"):
            assert field not in text, (
                f"{path.name} must not contain {field} (it belongs in trials/)"
            )


def test_the_real_trial_file_loads():
    db = load_database()
    assert [t.player for t in db.trials] == ["pilou"]
    assert db.fingerings["f6.palm"].cents == 13


def test_instrument_families_are_discovered_from_the_data_folder():
    from windfingerflow.database import families

    assert "saxophone" in families()
