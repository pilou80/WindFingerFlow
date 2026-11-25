"""Command line: ``windfingerflow score.musicxml -o annotated.musicxml --pdf annotated.pdf``."""

from __future__ import annotations

import argparse
import sys

from windfingerflow.instrument import SAX_OFFSET
from windfingerflow.models import Finger, Level
from windfingerflow.pipeline import run
from windfingerflow.profile import Profile


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="windfingerflow", description=__doc__)
    ap.add_argument("score", help="MusicXML, MEI, kern, ABC or MIDI file")
    ap.add_argument("-o", "--output", help="annotated MusicXML to write")
    ap.add_argument("--pdf", help="annotated PDF to write (rendered with Verovio)")
    ap.add_argument("--part", type=int, default=0, help="part index (default 0)")
    ap.add_argument("--sax", choices=sorted(SAX_OFFSET), help="convert sounding pitch to this sax")
    ap.add_argument("--level", choices=[lv.value for lv in Level], default="beginner")
    ap.add_argument("--exclude", action="append", default=[], help="fingering id to exclude")
    ap.add_argument("--unavailable", action="append", default=[], help="finger, e.g. R2")
    ap.add_argument(
        "--allow-unconfirmed", action="store_true", help="also suggest unverified fingerings"
    )
    ap.add_argument("--lang", default="en", choices=["en", "fr"])
    ap.add_argument("--all-notes", action="store_true", help="annotate standard fingerings too")
    args = ap.parse_args(argv)

    profile = Profile(
        level=Level(args.level),
        excluded_fingerings=set(args.exclude),
        unavailable_fingers={Finger(f) for f in args.unavailable},
        allow_unconfirmed=args.allow_unconfirmed,
    )
    result = run(
        args.score,
        part=args.part,
        sax=args.sax,
        profile=profile,
        lang=args.lang,
        all_notes=args.all_notes,
        musicxml_out=args.output,
        pdf_out=args.pdf,
    )
    for w in result.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e, f in zip(result.events, result.chosen, strict=True):
        print(f"{e.pitch:5} {e.duration:5.2f}  {f.id if f else '-'}")
    if args.output or args.pdf:
        print(f"{result.annotations} annotation(s) added", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
