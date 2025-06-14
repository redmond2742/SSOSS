from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import tempfile
import shutil
from typing import Optional

from . import ssoss_cli

app = FastAPI(title="SSOSS Web API")

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
    <body>
    <h1>SSOSS Web Interface</h1>
    <form action='/process' method='post' enctype='multipart/form-data'>
      Static Object CSV: <input type='file' name='static_object_file'><br>
      GPX File: <input type='file' name='gpx_file'><br>
      Video File: <input type='file' name='video_file'><br>
      Sync Frame: <input type='number' name='sync_frame'><br>
      Sync Timestamp: <input type='text' name='sync_timestamp'><br>
      Autosync Filename Timestamp <input type='checkbox' name='autosync'><br>
      Frame Extract Start: <input type='number' name='frame_extract_start'><br>
      Frame Extract End: <input type='number' name='frame_extract_end'><br>
      Label <input type='checkbox' name='label'><br>
      GIF <input type='checkbox' name='gif'><br>
      Bounding Box <input type='checkbox' name='bbox'><br>
      <input type='submit'>
    </form>
    </body>
    </html>
    """


def save_upload(upload: Optional[UploadFile], dst: Path) -> Optional[Path]:
    if upload is None:
        return None
    path = dst / upload.filename
    with path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path

@app.post("/process")
async def process(
    static_object_file: Optional[UploadFile] = File(None),
    gpx_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
    sync_frame: Optional[int] = Form(None),
    sync_timestamp: Optional[str] = Form(None),
    autosync: bool = Form(False),
    frame_extract_start: Optional[int] = Form(None),
    frame_extract_end: Optional[int] = Form(None),
    label: bool = Form(False),
    gif: bool = Form(False),
    bbox: bool = Form(False),
):
    workdir = Path(tempfile.mkdtemp(prefix="ssoss_"))

    so_path = save_upload(static_object_file, workdir)
    gpx_path = save_upload(gpx_file, workdir)
    vid_path = save_upload(video_file, workdir)

    vid_sync = ("", "")
    frame_extract = ("", "")
    if autosync and vid_path is not None:
        ts = ssoss_cli._timestamp_from_filename(vid_path.name)
        vid_sync = (1, ts)
    elif sync_frame is not None and sync_timestamp is not None:
        vid_sync = (sync_frame, sync_timestamp)
    if frame_extract_start is not None and frame_extract_end is not None:
        frame_extract = (frame_extract_start, frame_extract_end)

    extra_out = (label, gif, bbox, False)

    so_f = open(so_path, "r") if so_path else None
    gpx_f = open(gpx_path, "r") if gpx_path else None
    vid_f = open(vid_path, "r") if vid_path else None
    try:
        ssoss_cli.args_static_obj_gpx_video(
            generic_so_file=so_f,
            gpx_file=gpx_f,
            video_file=vid_f,
            vid_sync=vid_sync,
            frame_extract=frame_extract,
            extra_out=extra_out,
            autosync=autosync,
        )
    finally:
        for fh in (so_f, gpx_f, vid_f):
            if fh:
                fh.close()

    return JSONResponse({"output_dir": str(workdir)})


def main():
    import uvicorn
    uvicorn.run("ssoss.web_api:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
