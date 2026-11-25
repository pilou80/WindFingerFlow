"""Load and cross-validate the YAML data under ``data/``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from windfingerflow.models import Finger, Fingering, FingeringFile, Key, KeyCatalogue

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class DataError(ValueError):
    """Raised when the data files are inconsistent."""


@dataclass
class Database:
    keys: dict[str, Key]
    fingerings: dict[str, Fingering]

    def fingers_for(self, fingering: Fingering) -> set[Finger]:
        """Fingers used by a fingering, derived from the keys it presses."""
        return {self.keys[k].finger for k in fingering.keys}

    def candidates(self, pitch: str) -> list[Fingering]:
        return [f for f in self.fingerings.values() if pitch in f.pitches]


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_database(family: str = "saxophone", data_dir: Path = DEFAULT_DATA_DIR) -> Database:
    catalogue = KeyCatalogue.model_validate(_load_yaml(data_dir / "keys" / f"{family}.yaml"))
    keys = catalogue.by_id()
    if len(keys) != len(catalogue.keys):
        raise DataError("duplicate key ids in the key catalogue")

    fingerings: dict[str, Fingering] = {}
    for path in sorted((data_dir / "fingerings" / family).glob("*.yaml")):
        parsed = FingeringFile.model_validate(_load_yaml(path))
        for fingering in parsed.fingerings:
            if fingering.id in fingerings:
                raise DataError(f"duplicate fingering id {fingering.id!r} ({path.name})")
            unknown = [k for k in fingering.keys if k not in keys]
            if unknown:
                raise DataError(f"{fingering.id}: unknown keys {unknown}")
            fingerings[fingering.id] = fingering
    return Database(keys=keys, fingerings=fingerings)
