# AGENTS.md

Guide for LLM coding agents (and humans) adding features to WindFingerFlow.
Read this first, then `docs/design-notes.md` (design, data sources, open questions) and `CONTRIBUTING.md`.

## What the project does

Reads a score (MusicXML, MuseScore...), picks a fingering for each note of a woodwind line, and suggests
**alternate fingerings** where they help. Outputs an annotated PDF / MusicXML, and web pages
(score annotation, whole-range fingering chart, key reference page). Saxophone first; the instrument is a
data definition so other woodwinds can follow.

## Setup and checks (run before every commit)

```
uv sync                      # or: python -m venv .venv && pip install -e ".[dev]"
uv run ruff format .
uv run ruff check .          # strict: implicit string concatenation must be parenthesised (ISC004)
uv run pytest -q             # must be green; fix the test or the code, never skip a test
```

Python 3.12+. Run the web app with `uvicorn windfingerflow.web.app:app`; CLI: `windfingerflow --help`.

## Layout

- `data/saxophone/keys.yaml`: the key catalogue (ids like `lh.b`, `rh.side_bb`, finger, group).
- `data/saxophone/fingering/*.yaml`: fingerings (keys pressed, pitches, category, level, validation, sources).
- `data/saxophone/translations/<lang>.yaml`: every translatable text of the data (names, French abbreviations,
  descriptions, use / avoid). Never put names or descriptions in the key or fingering files.
- `data/i18n/<lang>.yaml`: every user-interface text (web, chart, key page, appendix, legend); read via `i18n.ui()`.
- `src/windfingerflow/`
  - `models.py` (strict pydantic models), `database.py` (loads and validates the YAML),
  - `profile.py` (player options), `chooser.py` (dynamic programming: standard vs alternate),
  - `score.py`, `score_parts.py`, `instrument.py` (transposition, ranges), `annotate.py`, `pipeline.py`, `cli.py`,
  - rendering: `render.py` (Verovio + cairosvg + PDF), `fiati.py` (fingering diagrams), `chart.py`, `keyschart.py`,
    `appendix.py`, `legend.py` (colour code), `buildinfo.py` (watermark with the git sha1),
  - `web/` (FastAPI + Jinja2 + HTMX): `app.py`, `strings.py` (EN/FR texts), `templates/`.
- `tests/`: one file per feature. `fonts/`: Fiati and Bravura (OFL). `docs/`: design notes.

## Rules that matter

**Data is the product. Never invent fingerings.**
- Every fingering needs `sources`. If you are not sure of the keys, set `needs_confirmation: true`,
  `validated: false` and write a source starting with `UNVERIFIED:`. Do not cite a page you did not read.
- `level`: `beginner` < `advanced` < `expert` < `experimental`. `validated: true` only when a player has tried it
  and said so (add the date and who in `sources`). Unvalidated fingerings are shown in orange as "to test".
- Altissimo (above F#6) is opt-in (`Profile.allow_altissimo`), so new high-register data goes in `altissimo.yaml`.
- Keys must exist in the catalogue; the octave key is added automatically by the register rules, do not list it.

**Never commit copyrighted scores** (the `local/` folder is git-ignored). Tests build their own tiny scores.

**Licences.** Code AGPL-3.0, data CC BY-SA 4.0, fonts keep their own licence. Do not add images, fonts or
data with an incompatible licence (no NonCommercial / NoDerivs). Record the author and licence of anything added.

**Commits** use the DCO: `git commit -s` (`Signed-off-by:`). No CLA.

## Conventions

- Every user-visible text lives in a per-language file (see above), in English and French; English is the fallback.
  A new text means a new entry in every `i18n/<lang>.yaml` (`tests/test_translations.py` fails otherwise).
- Generated SVG/PDF pages carry the grey watermark (name, version sha1, parameters). New outputs must add it
  via `buildinfo.add_watermark` and list their options in `watermark_text(...)`.
- Web: uploads are limited to 10 MB, SVG previews are served in an `<iframe>` under a strict CSP, the fonts route
  is a whitelist. Keep these properties when adding routes; validate every form value.
- Prefer small, typed functions and a test that fails without your change. Use fixed fingerings in tests
  rather than the chooser's output when the test is not about the chooser (the data changes often).
- Keep changes focused; do not reformat unrelated files.

## Adding a feature: checklist

1. Data change? Edit the YAML, then update `tests/test_validated_set.py` if the set of unvalidated fingerings moves.
2. New option? Add it to `Profile` or the function arguments, the CLI flag, the web form (both pages if relevant),
   both languages, the watermark, and a test.
3. New page or output? Reuse `render.py` and the watermark; add a download route and a test in `tests/test_web.py`.
4. Run format, lint and tests. Describe in the commit message what changed and why.
