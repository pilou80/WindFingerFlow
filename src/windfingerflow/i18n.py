"""User interface texts, one YAML file per language under ``data/i18n/``."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml

I18N_DIR = Path(__file__).resolve().parents[2] / "data" / "i18n"
DEFAULT_LANG = "en"


@cache
def _load(lang: str) -> dict:
    with (I18N_DIR / f"{lang}.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def languages() -> list[str]:
    """Language codes with a UI file, default language first."""
    found = sorted(p.stem for p in I18N_DIR.glob("*.yaml"))
    return sorted(found, key=lambda x: (x != DEFAULT_LANG, x))


def language_names() -> dict[str, str]:
    return {lang: _load(lang)["language_name"] for lang in languages()}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for key, value in over.items():
        out[key] = (
            _merge(out[key], value)
            if isinstance(value, dict) and isinstance(out.get(key), dict)
            else value
        )
    return out


def ui(lang: str, section: str) -> dict:
    """Texts of one section of the UI, with English filling any gap."""
    english = _load(DEFAULT_LANG)[section]
    if lang == DEFAULT_LANG or lang not in languages():
        return english
    return _merge(english, _load(lang).get(section, {}))


def pick_language(accept_language: str | None) -> str:
    prefix = (accept_language or "").strip().lower()[:2]
    return prefix if prefix in languages() else DEFAULT_LANG
