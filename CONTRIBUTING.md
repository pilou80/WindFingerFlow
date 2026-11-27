# Contributing

- Code and docs are in English.
- Sign off every commit (`git commit -s`) to certify the
  [Developer Certificate of Origin](https://developercertificate.org/). No CLA.
- Code is AGPL-3.0; contributions to the instrument data are CC BY-SA 4.0.
- The data of each instrument family lives in its own repository, included here as a git submodule
  (`data/saxophone` is `windfingerflow-data-saxophone`). Clone with `git clone --recurse-submodules`, or run
  `git submodule update --init` afterwards. Data changes are committed and pushed in the data repository first,
  then the submodule pointer is bumped here.
- Fingering data: write your own records and cite sources. Never copy text or images from
  protected charts or guides.
- Tests use public-domain or self-written scores only.
- Lint/format with `ruff`, test with `pytest`.
