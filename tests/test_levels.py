from windfingerflow.chooser import candidates
from windfingerflow.database import load_database
from windfingerflow.models import Level
from windfingerflow.profile import Profile


def test_fork_e_and_long_d_are_expert_fingerings():
    """pilou cannot play them yet; that does not make them wrong (2026-11-26)."""
    db = load_database()
    for fid in ("e6.fork", "d.long"):
        assert db.fingerings[fid].level == Level.EXPERT, fid
    pitch = {"e6.fork": "E6", "d.long": "D5"}
    for fid, note in pitch.items():
        advanced = {
            f.id
            for f in candidates(db, note, Profile(level=Level.ADVANCED, allow_unconfirmed=True))
        }
        expert = {
            f.id for f in candidates(db, note, Profile(level=Level.EXPERT, allow_unconfirmed=True))
        }
        assert fid not in advanced and fid in expert
