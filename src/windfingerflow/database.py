"""Load and cross-validate the YAML data under ``data/``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from windfingerflow.models import (
    Finger,
    Fingering,
    FingeringFile,
    I18n,
    Key,
    KeyCatalogue,
    TrialFile,
)
from windfingerflow.trials import apply_trials

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class DataError(ValueError):
    """Raised when the data files are inconsistent."""


@dataclass
class Database:
    keys: dict[str, Key]
    fingerings: dict[str, Fingering]
    languages: list[str]
    trials: list[TrialFile] = field(default_factory=list)

    def fingers_for(self, fingering: Fingering) -> set[Finger]:
        """Fingers used by a fingering, derived from the keys it presses."""
        return {self.keys[k].finger for k in fingering.keys}

    def candidates(self, pitch: str) -> list[Fingering]:
        return [f for f in self.fingerings.values() if pitch in f.pitches]


def families(data_dir: Path = DEFAULT_DATA_DIR) -> list[str]:
    """Instrument families available under ``data/``: the folders that hold a ``keys.yaml``."""
    return sorted(p.parent.name for p in data_dir.glob("*/keys.yaml"))


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_translations(folder: Path) -> dict[str, dict]:
    """{language: {"keys": {...}, "fingerings": {...}}} from translations/<lang>.yaml."""
    out = {}
    for path in sorted(folder.glob("*.yaml")):
        out[path.stem] = _load_yaml(path) or {}
    if "en" not in out:
        raise DataError(f"{folder}: the English translation file (en.yaml) is required")
    return out


def _texts(translations: dict[str, dict], section: str, item: str, field: str) -> I18n:
    return I18n(
        texts={
            lang: str(data[section][item][field])
            for lang, data in translations.items()
            if field in (data.get(section) or {}).get(item, {})
        }
    )


def load_database(family: str = "saxophone", data_dir: Path = DEFAULT_DATA_DIR) -> Database:
    folder = data_dir / family
    catalogue = KeyCatalogue.model_validate(_load_yaml(folder / "keys.yaml"))
    keys = catalogue.by_id()
    if len(keys) != len(catalogue.keys):
        raise DataError("duplicate key ids in the key catalogue")

    fingerings: dict[str, Fingering] = {}
    for path in sorted((folder / "fingering").glob("*.yaml")):
        parsed = FingeringFile.model_validate(_load_yaml(path))
        for fingering in parsed.fingerings:
            if fingering.id in fingerings:
                raise DataError(f"duplicate fingering id {fingering.id!r} ({path.name})")
            unknown = [k for k in fingering.keys if k not in keys]
            if unknown:
                raise DataError(f"{fingering.id}: unknown keys {unknown}")
            fingerings[fingering.id] = fingering

    trials = [
        TrialFile.model_validate(_load_yaml(path))
        for path in sorted((folder / "trials").glob("*.yaml"))
    ]
    for trial in trials:
        unknown = sorted({r.fingering for r in trial.results} - set(fingerings))
        if unknown:
            raise DataError(
                f"trials of {trial.player} ({trial.instrument}): unknown fingerings {unknown}"
            )
    for fid in list(fingerings):
        fingerings[fid] = apply_trials(fingerings[fid], trials)

    translations = _load_translations(folder / "translations")
    for lang, data in translations.items():
        for section, known in (("keys", keys), ("fingerings", fingerings)):
            stray = set(data.get(section) or {}) - set(known)
            if stray:
                raise DataError(f"translations/{lang}.yaml: unknown {section} {sorted(stray)}")
    for key in keys.values():
        keys[key.id] = key.model_copy(
            update={
                "name": _texts(translations, "keys", key.id, "name"),
                "abbr": _texts(translations, "keys", key.id, "abbr"),
                "availability": _texts(translations, "keys", key.id, "availability"),
                "description": _texts(translations, "keys", key.id, "description"),
            }
        )
    for f in fingerings.values():
        fingerings[f.id] = f.model_copy(
            update={
                "name": _texts(translations, "fingerings", f.id, "name"),
                "use": _texts(translations, "fingerings", f.id, "use"),
                "avoid": _texts(translations, "fingerings", f.id, "avoid"),
            }
        )
    missing = [i for i, k in keys.items() if not k.name.en] + [
        i for i, f in fingerings.items() if not f.name.en
    ]
    if missing:
        raise DataError(f"no English name for: {missing}")
    return Database(keys=keys, fingerings=fingerings, languages=sorted(translations), trials=trials)
