"""The whole job in one call, shared by the CLI and the web app."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from music21 import stream

from windfingerflow.annotate import annotate
from windfingerflow.appendix import appendix_svg_pages, collect_entries
from windfingerflow.chooser import Step, choose
from windfingerflow.database import load_database
from windfingerflow.models import Fingering
from windfingerflow.profile import Profile
from windfingerflow.render import render_pdf
from windfingerflow.score import NoteEvent, extract_line, load_score, range_warnings


@dataclass
class Result:
    events: list[NoteEvent]
    chosen: list[Fingering | None]
    warnings: list[str]
    annotations: int = 0
    pages: int = 0
    score: stream.Score | None = field(default=None, repr=False)


def run(
    source: str | Path,
    *,
    part: int = 0,
    sax: str | None = None,
    profile: Profile | None = None,
    lang: str = "en",
    all_notes: bool = False,
    style: str = "text",
    appendix: bool = False,
    musicxml_out: str | Path | None = None,
    pdf_out: str | Path | None = None,
) -> Result:
    db = load_database("saxophone")
    score = load_score(source)
    parts = getattr(score, "parts", None)
    if parts and not 0 <= part < len(parts):
        raise ValueError(f"part {part} does not exist (the score has {len(parts)} part(s))")
    events = extract_line(score, part, sax)
    chosen = choose(db, [Step(e.pitch, e.duration) for e in events], profile)
    result = Result(events, chosen, range_warnings(events), score=score)
    if musicxml_out or pdf_out:
        result.annotations = annotate(events, chosen, lang, all_notes, style)
        xml = Path(musicxml_out) if musicxml_out else Path(str(pdf_out) + ".musicxml")
        score.write("musicxml", fp=str(xml))
        if pdf_out:
            extra = []
            if appendix:
                extra = appendix_svg_pages(collect_entries(events, chosen), lang)
            result.pages = render_pdf(xml, pdf_out, extra)
            if not musicxml_out:
                xml.unlink(missing_ok=True)
    return result
