"""Command line: ``windfingerflow score.musicxml -o annotated.musicxml``."""

from __future__ import annotations

import argparse
import sys

from windfingerflow.annotate import annotate
from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.models import Finger, Level
from windfingerflow.profile import Profile
from windfingerflow.score import extract_line, load_score


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="windfingerflow", description=__doc__)
    ap.add_argument("score", help="MusicXML, MEI, kern, ABC or MIDI file")
    ap.add_argument("-o", "--output", help="annotated MusicXML to write")
    ap.add_argument("--part", type=int, default=0, help="part index (default 0)")
    ap.add_argument("--level", choices=[lv.value for lv in Level], default="beginner")
    ap.add_argument("--exclude", action="append", default=[], help="fingering id to exclude")
    ap.add_argument("--unavailable", action="append", default=[], help="finger, e.g. R2")
    ap.add_argument("--lang", default="en", choices=["en", "fr"])
    ap.add_argument("--all-notes", action="store_true", help="annotate standard fingerings too")
    args = ap.parse_args(argv)

    db = load_database("saxophone")
    profile = Profile(
        level=Level(args.level),
        excluded_fingerings=set(args.exclude),
        unavailable_fingers={Finger(f) for f in args.unavailable},
    )
    score = load_score(args.score)
    events = extract_line(score, args.part)
    chosen = choose(db, [Step(e.pitch, e.duration) for e in events], profile)
    for e, f in zip(events, chosen, strict=True):
        label = f.id if f else "-"
        print(f"{e.pitch:5} {e.duration:5.2f}  {label}")
    if args.output:
        n = annotate(events, chosen, args.lang, args.all_notes)
        score.write("musicxml", fp=args.output)
        print(f"{n} annotation(s) written to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
