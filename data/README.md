# Data

Fingering databases and texts (YAML), licensed **CC BY-SA 4.0**. Every fingering cites its sources.

```
data/
  saxophone/                 one folder per instrument
    keys.yaml                key catalogue: ids, finger, group (no translatable text)
    fingering/*.yaml         fingerings: keys pressed, pitches, category, level, validation, sources
    translations/<lang>.yaml names, abbreviations, availability, descriptions, use / avoid
  i18n/<lang>.yaml           user interface texts (web pages, chart, key page, appendix, legend)
```

Adding a language: add `translations/<lang>.yaml` and `i18n/<lang>.yaml` with the same ids and keys.
English is required and is the fallback; `tests/test_translations.py` checks that every language is complete.
