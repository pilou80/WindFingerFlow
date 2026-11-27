<img src="src/windfingerflow/web/static/logo.svg" alt="WindFingerFlow logo" width="96" align="right">

# WindFingerFlow

Reads a score (MusicXML first), analyses the melodic line and **suggests alternate woodwind
fingerings**, then returns an **annotated PDF** and an annotated MusicXML.

Starts with the saxophone; the instrument is a data definition so other woodwinds can follow.

> Status: pre-development. See [docs/design-notes.md](docs/design-notes.md).

## Licenses

- Code: AGPL-3.0 (see `LICENSE`)
- Data (one repository per instrument family, git submodules in `data/`, e.g. `data/saxophone`): CC BY-SA 4.0
- Fonts in `fonts/` keep their own licenses (Fiati: OFL 1.1)

## Contributing

Clone with `git clone --recurse-submodules` (the data are submodules). See [CONTRIBUTING.md](CONTRIBUTING.md). Coding agents (LLMs): start with [AGENTS.md](AGENTS.md). Contributions use the DCO (`Signed-off-by`), no CLA.
