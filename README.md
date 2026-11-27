<img src="src/windfingerflow/web/static/logo.svg" alt="WindFingerFlow logo" width="96" align="right">

# WindFingerFlow

Reads a score (MusicXML first), analyses the melodic line and **suggests alternate woodwind
fingerings**, then returns an **annotated PDF** and an annotated MusicXML.

Starts with the saxophone; the instrument is a data definition so other woodwinds can follow.

> Status: pre-development. See [docs/design-notes.md](docs/design-notes.md).

## Technologies

| Area | What is used |
|---|---|
| Language, tooling | Python 3.12+ (3.13 in the container), [uv](https://docs.astral.sh/uv/) for environments and lock file, [ruff](https://docs.astral.sh/ruff/) for lint and format, pytest, GitHub Actions CI |
| Score reading and transposition | [music21](https://www.music21.org/): MusicXML, MEI, kern, ABC and MIDI input, sax transposition, annotations |
| Choice of fingerings | A dynamic-programming search (Viterbi) over the candidates of each note: key changes, finger slides, intonation, effort |
| Score engraving | [Verovio](https://www.verovio.org/) renders the annotated score to SVG; [CairoSVG](https://cairosvg.org/) and [pypdf](https://pypdf.readthedocs.io/) build the PDF |
| Fingering diagrams and notation | [Fiati](https://github.com/ddoo/fiati) font for the key diagrams (OFL) and [Bravura](https://github.com/steinbergmedia/bravura) (SMuFL) for the staves of the charts |
| Data | YAML files validated with [pydantic](https://docs.pydantic.dev/) v2 (strict models), one git submodule per instrument family; player results kept apart in `trials/`; UI texts in one file per language |
| Web | [FastAPI](https://fastapi.tiangolo.com/) + Jinja2 + [HTMX](https://htmx.org/), SVG previews in sandboxed iframes, EN/FR interface with a language selector |
| Deployment | Docker (compose), behind a Caddy reverse proxy |

## Licenses

- Code: AGPL-3.0 (see `LICENSE`)
- Data (one repository per instrument family, git submodules in `data/`, e.g. `data/saxophone`): CC BY-SA 4.0
- Fonts in `fonts/` keep their own licenses (Fiati: OFL 1.1)

## Contributing

Clone with `git clone --recurse-submodules` (the data are submodules). See [CONTRIBUTING.md](CONTRIBUTING.md). Coding agents (LLMs): start with [AGENTS.md](AGENTS.md). Contributions use the DCO (`Signed-off-by`), no CLA.
