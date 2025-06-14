from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import shutil

app = FastAPI()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(upload: UploadFile, allowed_exts: set[str]):
    ext = Path(upload.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Invalid file type")
    dest = UPLOAD_DIR / upload.filename
    with dest.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return {"filename": upload.filename}


@app.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    """Accept a CSV file upload."""
    return _save_upload(file, {".csv"})


@app.post("/upload/gpx")
async def upload_gpx(file: UploadFile = File(...)):
    """Accept a GPX file upload."""
    return _save_upload(file, {".gpx"})


@app.post("/upload/video")
async def upload_video(file: UploadFile = File(...)):
    """Accept a video file upload."""
    # Accept a few common video extensions
    return _save_upload(file, {".mp4", ".mov", ".avi", ".mkv"})
