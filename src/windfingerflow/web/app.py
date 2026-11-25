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

from windfingerflow.instrument import SAX_OFFSET
from windfingerflow.models import Finger, Level
from windfingerflow.pipeline import run
from windfingerflow.profile import Profile
from windfingerflow.score import load_score
from windfingerflow.score_parts import default_part, list_parts
from windfingerflow.web.strings import pick

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


def _page(request: Request, name: str, **context):
    t = pick(request.headers.get("accept-language"))
    return templates.TemplateResponse(request, name, {"t": t, **context})


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _page(
        request,
        "index.html",
        saxes=list(SAX_OFFSET),
        levels=[lv.value for lv in Level],
        fingers=[f.value for f in Finger],
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
    style: str = Form("text"),
):
    t = pick(request.headers.get("accept-language"))

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
        or lang not in {"en", "fr"}
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
            musicxml_out=folder / "annotated.musicxml",
            pdf_out=folder / "annotated.pdf",
        )
    except Exception:  # untrusted input: never leak internals to the page
        log.exception("processing failed")
        shutil.rmtree(folder, ignore_errors=True)
        return error("err_parse")
    finally:
        source.unlink(missing_ok=True)
    rows = [
        (e.pitch, f.name.fr if lang == "fr" and f.name.fr else f.name.en if f else "-")
        for e, f in zip(result.events, result.chosen, strict=True)
        if f
    ]
    return _page(
        request,
        "result.html",
        job=job,
        rows=rows,
        notes=len(result.events),
        annotations=result.annotations,
        warnings=result.warnings,
        midi=suffix in {".mid", ".midi"},
    )


@app.post("/parts", response_class=HTMLResponse)
def parts(request: Request, file: UploadFile):
    """HTMX fragment: the part selector for an uploaded score."""
    t = pick(request.headers.get("accept-language"))
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


@app.get("/download/{job}/{kind}")
def download(job: str, kind: str):
    if not _ID_RE.match(job) or kind not in {"pdf", "musicxml"}:
        raise HTTPException(404)
    name = "annotated.pdf" if kind == "pdf" else "annotated.musicxml"
    path = WORKDIR / job / name
    if not path.is_file():
        raise HTTPException(404)
    media = "application/pdf" if kind == "pdf" else "application/vnd.recordare.musicxml+xml"
    return FileResponse(path, media_type=media, filename=name)
