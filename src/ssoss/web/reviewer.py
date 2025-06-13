import os
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncio

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _scan_unlabelled(src: Path, labels_csv: Path) -> List[Path]:
    labelled = set()
    if labels_csv.exists():
        with labels_csv.open(newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if row:
                    labelled.add(row[0])
    files = []
    for ext in IMAGE_EXTS:
        for p in src.rglob(f"*{ext}"):
            if p.name not in labelled:
                files.append(p)
    files.sort()
    return files


def create_app(src: Path) -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.on_event("startup")
    async def startup() -> None:
        app.state.src = src
        app.state.blocked_dir = src.parent / "blocked_signals"
        app.state.clear_dir = src.parent / "clear_signals"
        app.state.labels_csv = src.parent / "labels.csv"
        app.state.blocked_dir.mkdir(parents=True, exist_ok=True)
        app.state.clear_dir.mkdir(parents=True, exist_ok=True)
        app.state.lock = asyncio.Lock()
        app.state.queue = _scan_unlabelled(src, app.state.labels_csv)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        async with app.state.lock:
            path = app.state.queue[0] if app.state.queue else None
        img_id = path.relative_to(app.state.src).as_posix() if path else None
        return templates.TemplateResponse("index.html", {"request": request, "id": img_id})

    @app.get("/image/{img_id:path}")
    async def image(img_id: str) -> FileResponse:
        path = app.state.src / img_id
        if not path.exists():
            raise HTTPException(status_code=404)
        return FileResponse(str(path), media_type="image/jpeg")

    def _move(src_path: Path, dest_dir: Path) -> Path:
        dest = dest_dir / src_path.name
        n = 1
        while dest.exists():
            dest = dest_dir / f"{src_path.stem}_{n}{src_path.suffix}"
            n += 1
        src_path.replace(dest)
        return dest

    @app.post("/label", response_class=HTMLResponse)
    async def label(request: Request, id: str = Form(...), label: str = Form(...)) -> HTMLResponse:
        async with app.state.lock:
            match = None
            for i, p in enumerate(app.state.queue):
                if p.relative_to(app.state.src).as_posix() == id:
                    match = app.state.queue.pop(i)
                    break
        if match is None:
            raise HTTPException(status_code=404, detail="Image not queued")
        dest_dir = app.state.blocked_dir if label == "blocked" else app.state.clear_dir
        dest = _move(match, dest_dir)
        write_header = not app.state.labels_csv.exists()
        with app.state.labels_csv.open("a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["photo_name", "label", "timestamp_utc"])
            writer.writerow([dest.name, label, datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()])
        async with app.state.lock:
            next_path = app.state.queue[0] if app.state.queue else None
        next_id = next_path.relative_to(app.state.src).as_posix() if next_path else None
        return templates.TemplateResponse("fragment.html", {"request": request, "id": next_id})

    return app


# For uvicorn 'ssoss.web.reviewer:app'
_app_src = os.environ.get("SSOSS_PHOTO_SRC")
if _app_src:
    app = create_app(Path(_app_src))
else:
    app = FastAPI()
