# Data

One folder per instrument family. Each family is its own git repository, included here as a submodule, so a
family (saxophone, clarinet, flute...) can have its own contributors, history and releases, and can accumulate the
trials of several players and instruments.

```
data/
  saxophone/   submodule: https://github.com/pilou80/windfingerflow-data-saxophone (keys, fingerings, translations, trials)
  i18n/        user interface texts, one file per language (part of this repository)
```

A family folder is recognised by its `keys.yaml`. See the README of the family repository for the file layout, the
trial files and how to contribute. Licence of the data: CC BY-SA 4.0.

To add a family: create `windfingerflow-data-<family>` with the same layout, then
`git submodule add <url> data/<family>`.
