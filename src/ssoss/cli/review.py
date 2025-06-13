from __future__ import annotations

import os
from pathlib import Path
import click
import uvicorn

@click.command("review-photos")
@click.option("--src", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--port", type=int, default=8000, show_default=True)
def review_photos(src: str, port: int) -> None:
    """Launch photo review server."""
    os.environ["SSOSS_PHOTO_SRC"] = str(Path(src))
    uvicorn.run("ssoss.web.reviewer:app", host="0.0.0.0", port=port)
