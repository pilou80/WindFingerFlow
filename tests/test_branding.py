from fastapi.testclient import TestClient

from windfingerflow.branding import LOGO_PATH, logo_markup
from windfingerflow.chart import chart_svg_pages
from windfingerflow.database import load_database
from windfingerflow.keyschart import keys_svg_pages
from windfingerflow.web import app as webapp


def test_logo_file_exists_and_is_drawn_inline():
    assert LOGO_PATH.exists()
    markup = logo_markup(10, 20, 32)
    assert 'id="wff-logo"' in markup and "translate(10 20)" in markup and "<circle" in markup


def test_generated_pages_carry_the_logo():
    db = load_database()
    assert all('id="wff-logo"' in p for p in chart_svg_pages(db))
    assert all('id="wff-logo"' in p for p in keys_svg_pages(db))


def test_web_serves_the_logo_and_pages_use_it_as_favicon():
    client = TestClient(webapp.app)
    for path in ("/logo.svg", "/favicon.svg"):
        r = client.get(path)
        assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    for page in ("/", "/chart", "/keys"):
        html = client.get(page).text
        assert 'rel="icon" href="/logo.svg"' in html and 'src="/logo.svg"' in html, page
