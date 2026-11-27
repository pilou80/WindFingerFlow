"""FastAPI + HTMX web interface: upload a score, get an annotated PDF and MusicXML."""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from windfingerflow.branding import LOGO_PATH
from windfingerflow.buildinfo import watermark_text
from windfingerflow.chart import PAGE_H as CHART_H
from windfingerflow.chart import PAGE_W as CHART_W
from windfingerflow.chart import chart_svg_pages
from windfingerflow.database import load_database
from windfingerflow.fiati import FONTS_DIR
from windfingerflow.i18n import language_names, languages, pick_language, ui
from windfingerflow.instrument import SAX_OFFSET
from windfingerflow.keyschart import PAGE_H as KEYS_H
from windfingerflow.keyschart import PAGE_W as KEYS_W
from windfingerflow.keyschart import keys_svg_pages
from windfingerflow.models import Finger, Level
from windfingerflow.pipeline import run
from windfingerflow.profile import Profile
from windfingerflow.render import render_preview_pages, write_pdf
from windfingerflow.score import load_score
from windfingerflow.score_parts import default_part, list_parts

log = logging.getLogger("windfingerflow.web")

MAX_UPLOAD_BYTES = int(os.environ.get("WFF_MAX_UPLOAD_MB", "10")) * 1024 * 1024
ALLOWED_SUFFIXES = {".musicxml", ".xml", ".mxl", ".mei", ".krn", ".abc", ".mid", ".midi"}
RESULT_TTL_SECONDS = 3600
WORKDIR = Path(os.environ.get("WFF_WORKDIR", Path(tempfile.gettempdir()) / "windfingerflow"))
_ID_RE = re.compile(r"^[0-9a-f]{32}$")

app = FastAPI(title="WindFingerFlow")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _cleanup() -> None:
    if not WORKDIR.exists():
        return
    limit = time.time() - RESULT_TTL_SECONDS
    for entry in WORKDIR.iterdir():
        if entry.is_dir() and entry.stat().st_mtime < limit:
            shutil.rmtree(entry, ignore_errors=True)


LANG_COOKIE = "wff_lang"


def request_language(request: Request) -> str:
    """Interface language: ?ui=xx, else the remembered choice, else the browser's preference."""
    for candidate in (request.query_params.get("ui"), request.cookies.get(LANG_COOKIE)):
        if candidate in languages():
            return candidate
    return pick_language(request.headers.get("accept-language"))


@app.middleware("http")
async def remember_language(request: Request, call_next):
    response = await call_next(request)
    chosen = request.query_params.get("ui")
    if chosen in languages():
        response.set_cookie(LANG_COOKIE, chosen, max_age=365 * 24 * 3600, samesite="lax")
    return response


def _page(request: Request, name: str, **context):
    t = ui(request_language(request), "web")
    return templates.TemplateResponse(
        request,
        name,
        {"t": t, "languages": language_names(), "ui_lang": request_language(request), **context},
    )


@app.get("/logo.svg", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
def logo():
    return FileResponse(LOGO_PATH, media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _page(
        request,
        "index.html",
        saxes=list(SAX_OFFSET),
        levels=[lv.value for lv in Level],
        fingers=[f.value for f in Finger],
        lang_default=request_language(request),
    )


@app.post("/process", response_class=HTMLResponse)
def process(
    request: Request,
    file: UploadFile,
    part: int = Form(0),
    sax: str = Form(""),
    level: str = Form("beginner"),
    lang: str = Form("en"),
    unavailable: Annotated[list[str] | None, Form()] = None,
    exclude: str = Form(""),
    all_notes: bool = Form(False),
    allow_unconfirmed: bool = Form(False),
    altissimo: bool = Form(False),
    style: str = Form("text"),
    appendix: bool = Form(False),
):
    t = ui(request_language(request), "web")

    def error(key: str):
        return _page(request, "result.html", error=t[key])

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        return error("err_ext")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return error("err_size")
    if (
        sax not in SAX_OFFSET
        and sax != ""
        or level not in {lv.value for lv in Level}
        or lang not in languages()
        or style not in {"text", "diagram", "both"}
        or any(f not in {x.value for x in Finger} for f in unavailable or [])
    ):
        return error("err_parse")

    _cleanup()
    job = uuid.uuid4().hex
    folder = WORKDIR / job
    folder.mkdir(parents=True)
    source = folder / f"input{suffix}"
    source.write_bytes(data)
    profile = Profile(
        level=Level(level),
        excluded_fingerings={x.strip() for x in exclude.split(",") if x.strip()},
        unavailable_fingers={Finger(f) for f in unavailable or []},
        allow_unconfirmed=allow_unconfirmed,
        allow_altissimo=altissimo,
    )
    try:
        result = run(
            source,
            part=part,
            sax=sax or None,
            profile=profile,
            lang=lang,
            all_notes=all_notes,
            style=style,
            appendix=appendix,
            musicxml_out=folder / "annotated.musicxml",
            pdf_out=folder / "annotated.pdf",
        )
    except Exception:  # untrusted input: never leak internals to the page
        log.exception("processing failed")
        shutil.rmtree(folder, ignore_errors=True)
        return error("err_parse")
    finally:
        source.unlink(missing_ok=True)
    try:
        previews = []
        for n, (svg, w, h) in enumerate(
            render_preview_pages(folder / "annotated.musicxml", result.watermark), 1
        ):
            (folder / f"preview-{n}.svg").write_text(svg, encoding="utf-8")
            previews.append((n, round(w), round(h)))
    except Exception:
        log.exception("preview failed")
        previews = []
    return _page(
        request,
        "result.html",
        job=job,
        previews=previews,
        notes=len(result.events),
        annotations=result.annotations,
        warnings=result.warnings,
        midi=suffix in {".mid", ".midi"},
    )


@app.post("/parts", response_class=HTMLResponse)
def parts(request: Request, file: UploadFile):
    """HTMX fragment: the part selector for an uploaded score."""
    t = ui(request_language(request), "web")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        return _page(request, "parts.html", error=t["err_ext"])
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return _page(request, "parts.html", error=t["err_size"])
    _cleanup()
    folder = WORKDIR / uuid.uuid4().hex
    folder.mkdir(parents=True)
    try:
        source = folder / f"input{suffix}"
        source.write_bytes(data)
        info = list_parts(load_score(source))
    except Exception:
        log.exception("part listing failed")
        return _page(request, "parts.html", error=t["err_parse"])
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return _page(request, "parts.html", parts=info, default=default_part(info))


PREVIEW_HEADERS = {
    # The SVG is built from user-supplied scores: no script, no external loads, fonts from us only.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; font-src 'self'",
    "X-Content-Type-Options": "nosniff",
}


@app.get("/preview/{job}/{page}")
def preview(job: str, page: int):
    path = WORKDIR / job / f"preview-{page}.svg"
    if not _ID_RE.match(job) or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/svg+xml", headers=PREVIEW_HEADERS)


FONT_FILES = {"fiati-regular.ttf": "font/ttf", "Bravura.otf": "font/otf"}


@app.get("/fonts/{name}")
def font(name: str):
    if name not in FONT_FILES:
        raise HTTPException(404)
    return FileResponse(FONTS_DIR / name, media_type=FONT_FILES[name])


@app.get("/chart", response_class=HTMLResponse)
def chart_form(request: Request):
    lang = request_language(request)
    return _page(request, "chart.html", levels=[lv.value for lv in Level], lang_default=lang)


@app.post("/chart", response_class=HTMLResponse)
def chart_make(
    request: Request,
    naming: str = Form("letters"),
    level: str = Form("beginner"),
    lang: str = Form("en"),
    alternates: bool = Form(False),
    allow_unconfirmed: bool = Form(False),
    altissimo: bool = Form(False),
):
    t = ui(request_language(request), "web")
    if (
        naming not in {"letters", "solfege", "both"}
        or level not in {lv.value for lv in Level}
        or lang not in languages()
    ):
        return _page(request, "chart_result.html", error=t["err_parse"])
    _cleanup()
    job = uuid.uuid4().hex
    folder = WORKDIR / job
    folder.mkdir(parents=True)
    profile = Profile(
        level=Level(level), allow_unconfirmed=allow_unconfirmed, allow_altissimo=altissimo
    )
    db = load_database("saxophone")
    options = {"alternates": alternates, "lang": lang, "naming": naming}
    mark = watermark_text(
        "chart",
        naming=naming,
        lang=lang,
        level=level,
        alternates=alternates,
        unconfirmed=allow_unconfirmed,
        altissimo=altissimo,
    )
    try:
        write_pdf(chart_svg_pages(db, profile, watermark=mark, **options), folder / "chart.pdf")
        previews = []
        for n, svg in enumerate(
            chart_svg_pages(db, profile, responsive=True, watermark=mark, **options), 1
        ):
            (folder / f"preview-{n}.svg").write_text(svg, encoding="utf-8")
            previews.append((n, CHART_W, CHART_H))
    except Exception:
        log.exception("chart failed")
        shutil.rmtree(folder, ignore_errors=True)
        return _page(request, "chart_result.html", error=t["err_parse"])
    return _page(request, "chart_result.html", job=job, previews=previews)


@app.get("/keys", response_class=HTMLResponse)
def keys_form(request: Request):
    lang = request_language(request)
    return _page(request, "keys.html", lang_default=lang)


@app.post("/keys", response_class=HTMLResponse)
def keys_make(request: Request, lang: str = Form("en")):
    t = ui(request_language(request), "web")
    if lang not in languages():
        return _page(request, "chart_result.html", error=t["err_parse"])
    _cleanup()
    job = uuid.uuid4().hex
    folder = WORKDIR / job
    folder.mkdir(parents=True)
    db = load_database("saxophone")
    mark = watermark_text("keys", lang=lang)
    try:
        write_pdf(keys_svg_pages(db, lang=lang, watermark=mark), folder / "keys.pdf")
        previews = []
        for n, svg in enumerate(keys_svg_pages(db, lang=lang, responsive=True, watermark=mark), 1):
            (folder / f"preview-{n}.svg").write_text(svg, encoding="utf-8")
            previews.append((n, KEYS_W, KEYS_H))
    except Exception:
        log.exception("keys page failed")
        shutil.rmtree(folder, ignore_errors=True)
        return _page(request, "chart_result.html", error=t["err_parse"])
    return _page(request, "chart_result.html", job=job, previews=previews, pdf_kind="keys")


@app.get("/download/{job}/{kind}")
def download(job: str, kind: str):
    if not _ID_RE.match(job) or kind not in {"pdf", "musicxml", "chart", "keys"}:
        raise HTTPException(404)
    name = {
        "pdf": "annotated.pdf",
        "musicxml": "annotated.musicxml",
        "chart": "chart.pdf",
        "keys": "keys.pdf",
    }[kind]
    path = WORKDIR / job / name
    if not path.is_file():
        raise HTTPException(404)
    media = (
        "application/pdf"
        if kind in {"pdf", "chart", "keys"}
        else "application/vnd.recordare.musicxml+xml"
    )
    return FileResponse(path, media_type=media, filename=name)
