from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.profile import Profile


def test_unconfirmed_fingerings_are_opt_in():
    db = load_database()
    steps = [Step(p, 0.5) for p in ("C5", "D5", "C5")]
    default = choose(db, steps, Profile(level=Level.EXPERT))
    assert all(f is None or not f.needs_confirmation for f in default)
    opted_in = choose(db, steps, Profile(level=Level.EXPERT, allow_unconfirmed=True))
    assert any(f and f.id == "d.long" for f in opted_in)
