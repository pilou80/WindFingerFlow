from windfingerflow.database import load_database
from windfingerflow.i18n import _load, languages, ui


def flatten(data, prefix=""):
    for key, value in data.items():
        if isinstance(value, dict):
            yield from flatten(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}"


def test_every_language_translates_every_key_and_fingering():
    db = load_database()
    assert {"en", "fr"} <= set(db.languages)
    for lang in db.languages:
        for key in db.keys.values():
            assert key.name.texts.get(lang), (lang, key.id)
            assert key.availability.texts.get(lang), (lang, key.id)
            assert bool(key.description.texts.get(lang)) == bool(key.description.en), (lang, key.id)
        for f in db.fingerings.values():
            assert f.name.texts.get(lang), (lang, f.id)
            assert bool(f.use.texts.get(lang)) == bool(f.use.en), (lang, f.id)
            assert bool(f.avoid.texts.get(lang)) == bool(f.avoid.en), (lang, f.id)


def test_every_language_has_every_ui_text():
    english = set(flatten(_load("en")))
    for lang in languages():
        assert set(flatten(_load(lang))) == english, lang


def test_ui_falls_back_to_english_for_unknown_language():
    assert ui("xx", "chart") == ui("en", "chart")
