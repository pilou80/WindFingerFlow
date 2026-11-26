# WindFingerFlow — Design Notes

> Status: pre-development research & decisions (2026-11-25).
> No code has been written yet. This document gathers the research, decisions and open questions
> collected before starting implementation.

---

## 1. Goal

A tool that reads a score (MusicXML first), analyses the melodic line and **suggests alternate
woodwind fingerings**, then returns an **annotated PDF** (and an annotated MusicXML).

- Starts with **saxophone** (alto & tenor first; all saxophones share the same written fingerings).
- Architecture open to **other woodwinds** (clarinet, flute, oboe, bassoon…) later.
- Web UI where the user uploads a score, picks a **profile** (beginner / advanced / altissimo…)
  and **criteria**, and downloads the result.
- First deployment: personal use on a home server; open-source repository from the start.

---

## 2. Decisions summary

| Topic | Decision |
|---|---|
| Name | **WindFingerFlow** (package: `windfingerflow`) — reserve the GitHub repo name early |
| Repository | GitHub |
| Code license | **AGPL-3.0** |
| Data license (fingering databases) | **CC BY-SA 4.0** |
| Contributions | DCO (`Signed-off-by`), no CLA |
| Scope v1 | Saxophone; instrument = definition file, so other woodwinds = data, not rewrite |
| Language | Python **3.12** |
| Tooling | uv (deps), ruff (lint/format), pytest (tests), GitHub Actions (CI + Docker image) |
| Score parsing/analysis | **music21** |
| PDF rendering | **Verovio** (MuseScore CLI as optional engine later) |
| Web | **FastAPI** + server-rendered HTML + **HTMX** (no JS build step) |
| Architecture | Core library + **CLI** + **web service** |
| Processing | Synchronous (upload → PDF) |
| Outputs | PDF **and** annotated MusicXML |
| Input formats | MusicXML (`.musicxml`, `.xml`, `.mxl`), MEI, Humdrum kern, ABC; MIDI accepted with a warning; TinyNotation for tests. No `.mscz` / native notation files (ask users to export MusicXML). PDF/scans via Audiveris OMR later (§14) |
| Annotation | Configurable: text and/or fingering diagrams. Default = annotate **only non-standard fingerings**; option = all notes |
| Diagram font (v1) | **Fiati** (OFL 1.1) |
| Diagrams (later) | Own **SVG generator** (inspired by LilyPond woodwind diagrams) |
| PDF appendix (option) | Detailed page listing every alternate fingering used (large diagram, why, intonation, bars) |
| Development & docs | **English only** |
| UI & generated output | **English + French**, extensible (gettext) |
| Note naming | Separate setting from UI language: letters (C D E…), German letters (H/B), fixed-do solfège (do ré mi…) |
| Default pitch shown | **Written** pitch (concert pitch as option) |
| Deployment | Docker on home **Debian x86** server, access through **Tailscale** (no public port) |
| Public test corpus | Public-domain or self-written scores/exercises only |

---

## 3. Pipeline

```
Upload (MusicXML/ABC/MEI/kern)
  → parse (music21)
  → part selection, transposition, polyphony & range handling (see §3.1)
  → analyse the selected monophonic line(s)
  → candidate fingerings per note (instrument fingering DB)
  → filter by user profile (excluded fingerings, unavailable fingers, level)
  → choose fingering sequence (dynamic programming, context-weighted costs)
  → annotate score (text and/or Fiati diagrams)
  → render (Verovio → SVG → PDF) + optional appendix page
  → download PDF + annotated MusicXML
```

### 3.1 Part selection, transposition, polyphony, range

Uploaded files are not always a single saxophone part (piano score, quartet, orchestral excerpt…).

1. **Detect instruments** of every part (MusicXML part name / instrument metadata).
   - If saxophone part(s) exist → preselect them.
2. **No saxophone part** (e.g. piano, flute, violin, voice) → don't reject. Ask:
   "Which part do you want to play, and on which saxophone?" (reading other instruments' parts is a
   real use case).
3. **Transpose** concert pitch → written pitch of the chosen sax
   (soprano/tenor in Bb, alto/baritone in Eb). Parts already written for sax keep their transposition.
4. **Polyphony** (a sax plays one note at a time; piano = 2 staves, chords, several voices):
   - default: **top voice** (usually the melody, e.g. piano right hand);
   - option: user picks a staff/voice;
   - chords reported as a warning; only the extracted line is annotated.
5. **Range check** (written low Bb → high F#, per instrument model):
   - flag out-of-range notes;
   - suggest octave displacement, or altissimo fingerings if the profile allows them.
6. **Output options:**
   - annotate the extracted line in the original score, or
   - generate a **new single-staff saxophone part** (cleaner to read from).
7. **Multi-part files (e.g. SATB quartet):** user picks one part or **all parts**; each part is
   annotated for its own instrument (useful for quartet rehearsals).

---

## 4. Libraries & tools researched

### Score parsing / analysis
- **music21** (BSD-3-Clause) — chosen. Mature, reads/writes MusicXML, preserves fingerings on
  import, handles transposing instruments, reads Dorico MusicXML since v9.9. v10 series in 2026,
  requires recent Python (3.12+ per current README).
- **partitura** (Apache-2.0) — lighter alternative, explicit time model (useful for tempo/fast
  passages), loads MusicXML/MEI/kern/MIDI. Not chosen (less mature/elaborate than music21).

### Rendering
- **Verovio** (LGPL-3.0) — chosen. C++ engraving library with Python bindings (`pip install
  verovio`), renders MusicXML to SVG in-process; SVG → PDF via cairosvg + pypdf.
  JS version could provide in-browser preview.
- **MuseScore 4 CLI** (GPL, run as separate process) — best engraving quality; heavy.
  Headless with `QT_QPA_PLATFORM=offscreen` and `-o output.pdf`. Optional engine later.
- **LilyPond** — music21 can export to LilyPond (export quality considered imperfect);
  `musicxml2ly` also exists. Interesting mainly for its **woodwind diagrams** (see §7).

### Input formats readable by music21

| Format | Extensions | music21 support | Use in WindFingerFlow |
|---|---|---|---|
| MusicXML | `.musicxml`, `.xml`, `.mxl` | read & write | ✅ main input |
| MEI | `.mei` | read (export not yet implemented) | ✅ |
| Humdrum kern | `.krn` | read | ✅ (public-domain corpora for tests) |
| ABC | `.abc` | input only | ✅ |
| Capella | `.capx` | read | ⚠️ cheap to accept, niche |
| MuseData | `.md` | read | ⚠️ old academic format |
| Noteworthy | `.nwctxt`, `.nwc` | read | ⚠️ low priority |
| MIDI | `.mid`, `.midi` | read & write | ⚠️ accept with warning (no slurs/articulations, unreliable spelling) |
| TinyNotation | text string | input only | 🧪 unit tests |
| RomanText, ClercqTemperley, Volpiano, Scala | — | read | ❌ not relevant (harmony analysis, chant, scales) |

Output-only in music21: LilyPond, Braille, text. Not readable: native notation files
(MuseScore `.mscz`, Sibelius, Finale, Dorico) and PDF/scans (→ OMR, see §14).
File extensions above are from memory; check the converter source when implementing.

### Web
- **FastAPI** + Jinja2 templates + **HTMX**.
- Security (even on Tailscale): file size limit, format validation, treat uploaded XML as
  untrusted (music21 itself added a MusicXML security warning).

### Not reusable (checked)
- `instrumentbible/Woodwind-Fingerings` — no license, PNG images only, Max/MSP project.
- `Eolu/sax-fingering-chart` (Rust, MIDI → charts) — no license; interesting idea: choose
  fingering weighted by keys used for the previous note.
- "Saxophone Key Chart" (pages.dev) — JSON data with alternates but no author/license/repo.
- `fing` (PyPI, TOML fingering descriptions) — no license stated, no alternates/intonation.
  **Idea to reuse:** each key records **which finger presses it** (`press`), plus SVG layout section.

**Conclusion:** no open, reusable saxophone fingering database exists → WindFingerFlow's
fingering DB is a contribution in itself (hence CC BY-SA 4.0).

---

## 5. Data model

### 5.1 Instrument definition (one file per instrument)
- Key list (see §5.2), range, transposition, register rules (sax overblows at the octave;
  clarinet at the twelfth — different logic), instrument-specific cost weights.
- Variants derived from a base definition (soprano high G, baritone low A, adapted instruments,
  left-handed instruments).

### 5.1b Instrument model database (alongside the fingering DB)

Three layers:
1. **Key catalogue** per instrument family — every key that can exist (superset, see §5.3).
2. **Instrument types** — soprano, alto, tenor, baritone…: transposition, standard range,
   default key set.
3. **Model database** — one record per make/model (and generation when keywork changed):

| Field | Example |
|---|---|
| ID | `selmer.axos.tenor` |
| Make / model / type | Selmer / Axos / tenor |
| Years / generation | from… to… |
| Keys present | inherited from type ± differences (e.g. `+ rh.high_fs`, `- lh.front_f`) |
| Range | written low Bb → high F# |
| Key layout notes | e.g. alternate F# key position / finger |
| Known intonation tendencies | per note, with sources |
| Sources | manufacturer spec sheet, manual, user measurements |

- A user **setup** references a model (e.g. *Axos tenor + Selmer Concept mouthpiece*).
- Fingerings needing a key **missing on the model** are filtered out automatically.
- Intonation priority: **user measurement > model > general fingering data**.
- Stored under `data/`, licensed **CC BY-SA 4.0**, open to community contributions.
- Specs vary by production year/country → every record cites its source.
- Unknown model → fall back to the generic type; user ticks extra/missing keys manually.
- Example source: Selmer spec sheet gives the Axos tenor a range from low Bb to high F#.
  (YAS-475: to fill from Yamaha's spec sheet — do not guess.)

### 5.2 Key definition fields

| Field | Example (bis key) |
|---|---|
| ID | `lh.bis` |
| Hand & primary finger | left hand, index |
| Substitute finger(s) | — |
| Group | main / palm / side / pinky / thumb / octave |
| Display name (i18n) | "Bis key" / « Clé de Sib bis » |
| LilyPond mapping | `lh` + `bes` |
| Availability | all sizes / baritone only / soprano only / most modern models |
| Description | what the key is for |

Our own unambiguous IDs are needed because LilyPond names are ambiguous (`ees` = palm Eb in
`lh` and low Eb in `rh`; `bes` = bis in `lh` and side Bb in `rh`) and partly inherited from oboe.

### 5.3 Saxophone key list (alto/tenor) — draft

Finger notation: **L1–L4 / R1–R4** = index → little finger, left / right hand; **LT** = left thumb.

| ID | Name EN / FR | Primary finger | LilyPond | Availability |
|---|---|---|---|---|
| `lh.octave` | Octave key / Clé d'octave | LT | lh `T` | all |
| `lh.front_f` | Front F / Fa fourche (clé avant) | L1 | lh `front-f` | all (not some old models) |
| `lh.palm_d` | Palm D / Clé de paume Ré | L1 (knuckle; palm as substitute) | lh `d` | all |
| `lh.palm_eb` | Palm Eb / Clé de paume Mib | L1 (first joint) | lh `ees` | all |
| `lh.palm_f` | Palm F / Clé de paume Fa | L2 (first joint) | lh `f` | all |
| `lh.b` | B key / Clé de Si | L1 | cc `one` | all |
| `lh.bis` | Bis key / Clé de Sib bis | L1 (with B) | lh `bes` | all |
| `lh.a` | A key / Clé de La | L2 | cc `two` | all |
| `lh.g` | G key / Clé de Sol | L3 | cc `three` | all |
| `lh.gs` | G# key / Clé de Sol# | L4 | lh `gis` | all |
| `lh.low_cs` | Low C# / Do# grave | L4 | lh `cis` | all |
| `lh.low_b` | Low B / Si grave | L4 | lh `b` | all |
| `lh.low_bb` | Low Bb / Sib grave | L4 | lh `low-bes` | all |
| `lh.low_a` | Low A / La grave | LT | lh `low-a` | baritone only |
| `rh.f` | F key / Clé de Fa | R1 | cc `four` | all |
| `rh.e` | E key / Clé de Mi | R2 | cc `five` | all |
| `rh.d` | D key / Clé de Ré | R3 | cc `six` | all |
| `rh.alt_fs` | Alternate F# / Fa# alternatif | R3 (probable — **to confirm**) | rh `fis` | all |
| `rh.side_e` | Side E (high E) / Mi aigu latéral | R1 (side) | rh `e` | all |
| `rh.side_c` | Side C / Do latéral | R1 (side) | rh `c` | all |
| `rh.side_bb` | Side Bb / Sib de côté | R1 (side) | rh `bes` | all |
| `rh.high_fs` | High F# / Fa# aigu (4th side key) | R1 (side) | rh `high-fis` | most modern models |
| `rh.low_eb` | Low Eb / Mib grave | R4 (upper) | rh `ees` | all |
| `rh.low_c` | Low C / Do grave | R4 (lower) | **to check in LilyPond source** | all |
| `rh.high_g` | High G / Sol aigu | **to define** | — | some sopranos |

### 5.4 Fingering record (common DB, in the repo, YAML + validation schema)

| Field | Content |
|---|---|
| ID | e.g. `bb.side` |
| Written note(s) / octave(s) | e.g. Bb4, Bb5 (with octave key) |
| Keys pressed | list of key IDs |
| Fingers used | derived from keys (+ substitutes) |
| Category | standard / alternate / altissimo / trill |
| Level | beginner / advanced / expert |
| General intonation | sharp / in tune / flat, + cents if a source gives it |
| Tone & response | e.g. "duller", "unstable response" |
| Recommended use | fast passage, sustained note, trill with…, connects with… |
| Avoid when | e.g. B ↔ Bb with bis |
| Sources | WFG, Dawkes, methods, Navy Band, UNSW… (cite, never copy text/images) |

### 5.5 User profile (local, per user)
- **Setups**: instrument + mouthpiece (+ reed) — intonation depends on the mouthpiece too.
  Example: *Selmer Axos tenor + Selmer Concept*, *Yamaha YAS-475 alto + Selmer S90 190*.
- **Excluded fingerings** (experience or equipment).
- **Measured intonation** per fingering & setup (cents from a tuner) — overrides general value.
- **Preferences**: favour/penalise specific fingerings.
- **Finger availability** (accessibility): each finger (LT, L1–L4, R1–R4) = available / limited /
  unavailable; can be **temporary** (e.g. injured until a date).
  - unavailable → fingerings using it are excluded unless a substitute finger is possible;
  - limited → penalised, more strongly in fast passages;
  - the PDF can mention when a substitute finger is used.
- Storage: YAML file to start; SQLite later if needed.

---

## 6. Fingering selection algorithm

- Model: each note has candidate fingerings; transitions have a cost; find the cheapest path
  (**dynamic programming / Viterbi**), as done in the literature for guitar, piano and cello.
  Known limit: if costs only look at adjacent notes, the algorithm lacks lookahead.
- Cost terms (generic; weights per instrument):
  - number of keys/fingers that move;
  - **same finger sliding between keys** (pinky slides, L1 rolling B ↔ bis, R1 main ↔ side keys);
  - forks / cross-fingerings;
  - octave key changes;
  - tempo / note duration;
  - trills;
  - **intonation** — weighted by context: high weight on long/exposed/slow notes, low weight in
    fast passages (fluency wins);
  - user preferences, limited fingers.
- Hard filters: excluded fingerings, unavailable fingers, profile level.
- Profiles (draft):

| Profile | Example alternatives |
|---|---|
| Beginner | Bb/A#: bis, 1+1, side; F#: alternate |
| Advanced | Side C, fork F, trill fingerings, pinky slides (G#/C#/low B), palm keys |
| Altissimo | Above high F#; instrument-dependent, one table per setup, user-adjustable |

---

## 7. Diagrams & fonts

### Two output levels
1. **In the score (compact):** small Fiati diagram or short text ("Side Bb") above the note.
2. **Appendix page (optional, detailed, "Dawkes style"):** for each alternate fingering used:
   large diagram, name, why it was chosen, intonation, bars where it appears.

### Fonts (license is what matters: bundled + used on a server)

| Font | License | Verdict |
|---|---|---|
| **Fiati** | OFL 1.1 | ✅ **v1 default**. Multi-instrument, derived from Bravura's fingering section; used by MuseScore fingering plugins. Last push Oct 2023. Ship with its license in `fonts/`. |
| Legni Saxophone (+ flute, oboe, clarinet, bassoon) | OFL (paid download, ~6 USD) | ✅ possible; covers other woodwinds |
| Glyph3 Woodwinds | OFL 1.1 | ✅ for contemporary/extended techniques later |
| Saxy | no license stated | ❌ |
| Tristan Durie fonts | commercial; basic license forbids web/server/online-app use | ❌ |
| Woodwind Tablature Sax (M. Hindson) | free, license unverified | ⚠️ |
| MusicEd Fingerings | commercial | ❌ |

### LilyPond woodwind diagrams (reference / generator)
- Available for piccolo, flute, oboe, clarinet, bass clarinet, saxophone (soprano/alto/tenor/
  baritone variants), bassoon, contrabassoon.
- Written as markup: `\woodwind-diagram #'saxophone #'((cc . (...)) (lh . (...)) (rh . (...)))`
  — three groups: central column (`cc`), left-hand (`lh`), right-hand (`rh`) keys.
- Defined in Scheme: `scm/define-woodwind-diagrams.scm` (keys) and
  `scm/display-woodwind-diagrams.scm` (drawing). Drawn as vectors at engraving time.
- Options: key states (pressed, half, quarter/three-quarter, trill), graphical or text mode,
  size/thickness.
- Possible uses:
  1. model for our own SVG generator (structure, key positions, states);
  2. **build-time generator**: script creates one `.ly` per fingering → compile to SVG → store
     in the project (for the appendix), no LilyPond needed on the server.
     License of generated output to double-check before publishing.
- Plan: Fiati in score (v1) → LilyPond-generated SVG for appendix if needed → own SVG generator.

### Visual inspiration
- Dawkes "complete guide to alternatives": per section, short explanation + bold entries
  (fingering, use cases, sometimes intonation) + one diagram. Cite as a source; do not reuse
  images or text.
- To define: what we like in their diagrams (full sax view, colours, highlighting of the key that
  differs from the standard fingering, size) → spec for the SVG renderer.

---

## 8. Internationalisation

- Code, docs, README: **English only**.
- UI + generated PDF: **EN + FR**, extensible via **gettext/Babel** catalogs (one file per
  language; adding a language = adding a catalog, no code change).
- Fingering glossary is translatable too (e.g. Side Bb = Sib de côté, Fork F# = Fa# fourche,
  Palm keys = Clés de paume, Altissimo = Suraigu).
- **Note naming system** independent from UI language:
  - letters: C D E F G A B;
  - German letters: B natural = H, Bb = B;
  - fixed-do solfège: do ré mi fa sol la si (spelling per language: "Sib", "Si♭", "Si bemol"…).
- music21 uses English names internally; conversion only at display time.
- Later: community translations via Weblate (Hosted Weblate reportedly free for libre projects —
  to verify).

---

## 9. Licensing details

| Dependency | License | Compatible with AGPL-3.0 |
|---|---|---|
| music21 | BSD-3-Clause | ✅ |
| Verovio | LGPL-3.0 | ✅ |
| FastAPI | MIT | ✅ |
| Fiati font | OFL 1.1 | ✅ (ship license file) |
| MuseScore (optional) | GPL | ✅ (separate process) |

- Decide the license **before** opening the repo (relicensing later needs all contributors).
- Fingering data: write our own records, combining several sources, **citing** them.
  A key combination is a fact, but bulk-copying a protected chart's presentation is not OK.
  The Woodwind Fingering Guide is © Timothy Reichard → cite, don't scrape. (Not legal advice.)

---

## 10. Deployment

### v1 — home server
- Debian x86, existing Docker services → one more container (compose service).
- x86: Verovio & music21 install from wheels; MuseScore also possible later.
- Access via **Tailscale** only (optionally **Tailscale Serve** for HTTPS on the tailnet name).
- Usable from phone at rehearsal (upload score, get PDF).
- Minimal security: size limit + format validation.

### Later — public hosting (notes from research, Nov 2026)
- **Google Cloud Run**: scales to zero; free tier ~180,000 vCPU-seconds + 2M requests/month
  (request-based billing). Needs a card → set a budget alert.
- **Hetzner**: two price increases in 2026 (last 15 June 2026); cheap CX plans reported
  unavailable to new customers for a while → check at order time.
- **Hugging Face Spaces**: Docker Spaces now require a paid plan (free CPU Basic restricted
  around July 2026) → not suitable.
- Same Docker image runs anywhere (VPS, Cloud Run, home server).

---

## 11. Test corpus

### Policy
- Band (harmonie) scores are almost all copyrighted (arrangements too) → **local testing only,
  never committed**.
- Public tests: public-domain works **encoded by us**, or self-written exercises.
- Check the **edition**, not only the work: modern revisions (e.g. Marcel Mule's revision of
  Klosé) are still copyrighted → use original editions.

### Public-domain candidates (IMSLP — mostly PDF scans)

| Need | Work | Notes |
|---|---|---|
| Quartet SATB | Singelée, *Premier Quatuor* op. 53 (1857) | Often cited as the first sax quartet; soprano, alto, tenor, baritone in one piece |
| Quartet SATB | Léon Kreutzer, *Quatuor pour saxophones* (first ed. Adolphe Sax, c. 1863) | IMSLP also has a 2018 typeset edition with parts → check whether source files exist |
| Quartet SATB | Glazunov, Quartet op. 109 | IMSLP: most likely PD in the USA; Glazunov died 1936 → likely PD in EU; check the edition |
| Solo (any sax) | Klosé, *25 Exercices journaliers* (1881) | Classic technical studies |
| Solo (any sax) | Klosé, *25 Études de mécanisme* | Mechanical/technical studies |
| Solo baritone | Klosé, *Méthode complète de saxophone-baryton* | Baritone-specific material |

Fingerings depend on the written note, so Klosé studies and quartet parts cover soprano and tenor
solo needs too.

### Getting MusicXML
1. **Re-type** in MuseScore → export MusicXML → publish under CC BY-SA 4.0 with the data.
2. **Audiveris** on IMSLP scans + manual correction (doubles as a test of the future PDF input).
3. **Self-written exercises** for unit tests: Bb/F# passages, chromatic lines, trills, palm keys,
   pinky slides (TinyNotation or small MusicXML files).

### Local-only sources (never committed)
- User's band parts and purchased scores.
- MuseScore.com downloads (unless marked public domain / CC0 by the uploader).
- 8notes free arrangements (e.g. Glazunov op. 109 for sax quartet) — arrangements belong to 8notes.

### Robustness
- music21 ships the MIT-licensed LilyPond/MusicXML test suite → parser robustness tests
  (ties, tuplets, grace notes, multiple voices), even though it is not sax music.

### Test cases for §3.1
- Piano score (grand staff, chords) → top-voice extraction, transposition, range warnings.
- SATB quartet → per-part annotation, "all parts" mode.
- Non-sax melodic part (flute/violin) → transposition + range check.

---

## 12. Beginner fingering sample (draft)

Finger notation: L1–L4 / R1–R4 = index → little finger; LT = left thumb.

### Bb / A# (low & middle registers)

| ID | Name EN / FR | Keys | Fingers | Intonation | Use | Avoid |
|---|---|---|---|---|---|---|
| `bb.bis` | Bis Bb / Sib bis | `lh.b` + `lh.bis` | L1 (two keys) | reputedly good (source needed) | flat keys, no B natural nearby | B ↔ Bb (L1 must roll) |
| `bb.one_one` | 1 and 1 Bb / Sib 1+1 | `lh.b` + `rh.f` | L1, R1 | validated by pilou 2026-11-26 (advanced) | versatile; right hand already in place | fast passages where R1 must move quickly |
| `bb.side` | Side Bb / Sib de côté | `lh.b` + `lh.a` + `rh.side_bb` | L1, L2, R1 (side) | validated by pilou 2026-11-26 (advanced) | chromatic B–Bb–B, A–Bb trill | very flat keys if a simpler option exists |

Typical choice: B–Bb–B → side Bb; Bb–F–Bb → bis.

### F# / Gb (low & middle registers)

| ID | Name EN / FR | Keys | Fingers | Intonation | Use | Avoid |
|---|---|---|---|---|---|---|
| `fs.std` | Standard F# / Fa# standard | `lh.b` + `lh.a` + `lh.g` + `rh.e` | L1, L2, L3, R2 | reference | general case | — |
| `fs.alt` | Alternate F# / Fa# alternatif | `lh.b` + `lh.a` + `lh.g` + `rh.f` + `rh.alt_fs` | L1, L2, L3, R1, R3 (to confirm) | to measure | F ↔ F#, F–F# trill, chromatic E–F–F# | slow exposed notes until intonation checked |

The alternate F# key raises F by a semitone instead of using R2 (first & second octaves).
Accessibility example: if R2 is unavailable, standard F# is excluded but alternate F# stays playable.

### Additional alternates to add (from Dawkes guide, to rewrite in our own words)
- Middle Bb: flute-style Bb (besides side & bis).
- Middle C: side C (with L1 + B) — often **flatter** than standard → fast passages.
- Middle C#: L3 + octave key; venting with side C and/or side Bb; "D to C#" adjustment.
  Open C# is typically **flat** and lacks resonance; venting raises it.
- Long D: C + palm D.
- Alternative G# (left pinky).
- Venting: raise middle G, raise middle B, open low D.
- General: verify all with a tuner or drone; venting effects vary by instrument & setup.

### Known general intonation tendencies (sources: D'Addario/Jagow, US Navy Band, The Instrumentalist)
- Flat: third-space C# (open C#).
- Sharp: fourth-line D, D#/Eb, E; palm keys D, D#/Eb, E, F.
- Use intonation alternates where pitch is clearly heard: sustained/lyrical lines, exposed chords,
  slow tempi.
- "No two horns play the same" → justifies per-setup measured intonation.

---

## 13. Open questions / to verify
- [ ] Finger for the **alternate F#** key (R3 probable).
- [ ] **Low C** key name in LilyPond `define-woodwind-diagrams.scm`.
- [ ] **High G** (soprano) key definition.
- [ ] Common **substitute fingers** for keys (only palm D listed so far).
- [ ] Intonation values for the beginner sample (sources + measurements on user's horns).
- [ ] Whether Verovio can render Fiati glyphs inline.
- [ ] License status of LilyPond-generated SVG output.
- [ ] Visual spec for the future SVG renderer (inspired by Dawkes / LilyPond).
- [ ] Hosted Weblate terms for libre projects.

---

### Missing common fingerings, to validate (2026-11-26)

Listed from memory and NOT in the data yet: no key combination is written until a source or the saxophonist confirms it. Each one should enter as `experimental`, `validated: false`, `needs_confirmation: true`.

- Alternate Eb (D# 4/5/6) and alternate C# (5/6) fingerings.
- Alternates for the low notes (Bb3, B3, C4, C#4) that avoid moving the left little finger.
- Altissimo above F#6 (G6, A6, Bb6, C7...).
- Trill fingerings (for example G#-A#, B-C#).
- Tuning / ghost-note fingerings.
- Other alternates for Bb (thumb bis variants).

## 14. Future ideas
- **PDF / scanned score input via Audiveris (OMR)** — band scores often arrive as PDFs.
  - Open-source optical music recognition (Java), license **AGPL-3.0** (same as ours).
  - Recent stable release 5.10.2 (March 2026); installers for Linux (.deb), Windows, macOS;
    also on Flathub (x86_64, ~290 MiB installed).
  - Exports MusicXML 4.0 (a subset of its OMR data) + its own `.omr` project format.
  - Ships with an editor for checking/correcting recognition results → OMR output usually
    needs manual correction before fingering analysis.
  - Integration idea: optional pre-processing step (PDF → Audiveris CLI/batch → MusicXML →
    WindFingerFlow), in a separate container; flag the result as "OMR, please check".
  - To evaluate: batch/CLI mode, accuracy on band parts, processing time on the home server.
  - Repo: https://github.com/Audiveris/audiveris
- **Calibration mode**: play each fingering into a microphone, measure deviation in cents
  (aubio / librosa) and store it in the user profile.
- **OpenWInD** (Inria, `pip install openwind`): 1D finite-element modelling of wind instruments —
  possible way to *compute* intonation of rare fingerings (to evaluate).
- Other woodwinds: clarinet (pinky alternation L/R, throat-tone resonance fingerings, twelfth
  overblowing), flute (Bb thumb/1+1/lever, F# alternatives), oboe (forked F / left F), bassoon.
- In-browser score preview with Verovio JS.
- **3D saxophone model** to show the keys on a real instrument (candidate: https://sketchfab.com/3d-models/realistic-saxophone-1f5185760cdf4d6390d29b1df830bd8e). Not evaluated: check its licence (attribution, compatibility with AGPL) and export format before any use.
- MuseScore CLI as optional high-quality rendering engine.

---

### To do: photos of the keys on the keys page (asked 2026-11-26)

Show a photo of each key on the "Saxophone keys and their names" page. Either find freely licensed images (CC0, public domain or CC BY; avoid NonCommercial / NoDerivs, and check share-alike against the project licence) or have the saxophonist take the photos. Store the author and licence of each image next to it.

## 15. References
- music21 — https://github.com/cuthbertLab/music21 · https://www.music21.org/music21docs/
- partitura — https://github.com/CPJKU/partitura
- Verovio — https://pypi.org/project/verovio/
- MuseScore CLI — https://handbook.musescore.org/appendix/command-line-usage
- LilyPond woodwind diagrams — https://lilypond.org/doc/v2.27/Documentation/notation/woodwinds
- Fiati font — https://github.com/eduardomourar/fiati/releases
- MuseScore Fingering Diagram plugin — https://musescore.org/en/project/fingering-diagram
- MuseScore Alternate Fingerings plugin — https://github.com/lgvr123/musescore-alternatefingerings
- Legni fonts — https://www.subcontrabassoon.com/legnifont · https://www.subcontrabassoon.com/legnifont/download.html
- Fingering Diagram Builder (Bret Pimentel) — https://fingering.bretpimentel.com/help/
- Woodwind Fingering Guide (© T. Reichard, cite only) — https://www.wfg.woodwind.org/ · https://www.wfg.woodwind.org/sax/sax_fing.html
- Dawkes alternate fingerings guide — https://www.dawkes.co.uk/sound-room/saxophone-fingerings-a-complete-guide-to-alternatives/
- Saxophone intonation (Shelley Jagow, D'Addario) — https://www.dansr.com/resources/saxophone-intonation-tendencies-voicing-embouchure-and-alternate-fingerings
- US Navy Band sax intonation (archived) — https://webarchive.library.unt.edu/web/20120913080239/http:/www.navyband.navy.mil/article_sax4tet.shtml
- UNSW saxophone acoustics — https://www.phys.unsw.edu.au/music/saxophone/
- fing (PyPI) — https://pypi.org/project/fing/
- OpenWInD — https://pypi.org/project/openwind/
- Audiveris (OMR) — https://github.com/Audiveris/audiveris
- IMSLP – Singelée Quartet op. 53 — https://imslp.org/wiki/Saxophone_Quartet_No.1,_Op.53_(Singel%C3%A9e,_Jean_Baptiste)
- IMSLP – Kreutzer Quartet — https://imslp.org/wiki/Saxophone_Quartet_(Kreutzer,_Léon)
- IMSLP – Glazunov Quartet op. 109 — https://imslp.org/wiki/Saxophone_Quartet,_Op.109_(Glazunov,_Aleksandr)
- IMSLP – Klosé 25 Exercices journaliers — https://imslp.org/wiki/25_Exercices_journaliers_pour_le_Saxophone_(Klosé,_Hyacinthe_Eléonore)
- IMSLP – Klosé 25 Études de mécanisme — https://imslp.org/wiki/25_Études_de_mécanisme_pour_le_Saxophone_(Klosé,_Hyacinthe_Eléonore)
- IMSLP – Scores featuring the saxophone — https://imslp.org/wiki/Category:Scores_featuring_the_saxophone
- music21 subconverters (input/output formats) — https://music21.org/music21docs/moduleReference/moduleConverterSubConverters.html
- Google Cloud Run pricing — https://cloud.google.com/run/pricing
- Automatic fingering by dynamic programming (piano, Nichols & Raphael, ISMIR 2007) — https://archives.ismir.net/ismir2007/paper/000355.pdf
