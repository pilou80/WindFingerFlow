# Data

Fingering databases and texts (YAML), licensed **CC BY-SA 4.0**. Every fingering cites its sources.

```
data/
  saxophone/                 one folder per instrument
    keys.yaml                key catalogue: ids, finger, group (no translatable text)
    fingering/*.yaml         fingerings: keys pressed, pitches, category, level, validation, sources
    translations/<lang>.yaml names, abbreviations, availability, descriptions, use / avoid
    trials/<player>-<instrument>.yaml  what a player tried: validated, level, measured cents, notes
  i18n/<lang>.yaml           user interface texts (web pages, chart, key page, appendix, legend)
```

Adding a language: add `translations/<lang>.yaml` and `i18n/<lang>.yaml` with the same ids and keys.
English is required and is the fallback; `tests/test_translations.py` checks that every language is complete.

## Trials: results of the players

The fingering files hold reference data only (keys, pitches, category, reference level, sources). What a player
found goes in `trials/<player>-<instrument>.yaml`: whether the fingering works (`validated`), how demanding it is
(`level`), the measured intonation (`cents` against the file's `tuning`) and a free note. Several players and several
instruments accumulate side by side: a fingering counts as validated when any player validated it, its level is the
hardest one reported, and its intonation is derived from the mean of the measures (within +/-10 cents = in tune).
Never write `validated` or `cents` in a fingering file: `tests/test_trials.py` fails if you do.
