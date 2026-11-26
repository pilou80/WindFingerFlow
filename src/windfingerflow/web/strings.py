"""UI strings of the web pages: they live in data/i18n/<lang>.yaml (section ``web``)."""

from windfingerflow.i18n import pick_language, ui


def pick(accept_language: str | None) -> dict[str, str]:
    return ui(pick_language(accept_language), "web")
