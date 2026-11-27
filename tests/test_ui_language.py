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


def test_saxophone_names_are_translated():
    from windfingerflow.instrument import SAX_OFFSET

    client = TestClient(webapp.app)
    french = client.get("/?ui=fr").text
    assert ">Ténor<" in french and ">Baryton<" in french
    english = client.get("/?ui=en").text
    assert ">Tenor<" in english and ">Baritone<" in english
    assert set(SAX_OFFSET) == {"soprano", "alto", "tenor", "baritone"}  # keep the UI texts in step


def test_pages_show_the_version_and_a_github_link():
    from windfingerflow import __version__

    client = TestClient(webapp.app)
    for page in ("/", "/chart", "/keys"):
        html = client.get(page + "?ui=fr").text
        assert f"WindFingerFlow {__version__} (" in html, page
        assert 'href="https://github.com/pilou80/WindFingerFlow"' in html, page
        assert "Code source sur GitHub" in html, page
