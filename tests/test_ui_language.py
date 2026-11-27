from fastapi.testclient import TestClient

from windfingerflow.web import app as webapp


def test_language_selector_remembers_the_choice():
    client = TestClient(webapp.app)
    english = client.get("/", headers={"accept-language": "en"})
    assert '<html lang="en">' in english.text and "?ui=fr" in english.text
    french = client.get("/?ui=fr", headers={"accept-language": "en"})
    assert '<html lang="fr">' in french.text and "Doigtés alternatifs" in french.text
    assert "wff_lang=fr" in french.headers["set-cookie"]
    again = client.get("/chart", headers={"accept-language": "en"})  # cookie wins over the browser
    assert '<html lang="fr">' in again.text


def test_browser_language_is_the_default_and_bad_values_are_ignored():
    client = TestClient(webapp.app)
    assert '<html lang="fr">' in client.get("/", headers={"accept-language": "fr-FR"}).text
    other = TestClient(webapp.app)
    assert '<html lang="en">' in other.get("/?ui=xx", headers={"accept-language": "en"}).text
    assert "set-cookie" not in other.get("/?ui=xx").headers


def test_levels_are_translated_in_the_forms():
    client = TestClient(webapp.app)
    for page in ("/", "/chart"):
        french = client.get(page + "?ui=fr").text
        assert ">Débutant<" in french and ">Expérimental<" in french, page
        assert ">beginner<" not in french, page
