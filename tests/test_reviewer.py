import sys
import csv
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from ssoss.web import reviewer


def create_image(path: Path) -> None:
    img = Image.new("RGB", (10, 10), color="white")
    img.save(path)


def test_reviewer_flow(tmp_path):
    src = tmp_path / "unclassified"
    src.mkdir()
    create_image(src / "a.jpg")
    create_image(src / "b.jpg")

    app = reviewer.create_app(src)
    with TestClient(app) as client:
        client.get("/")
        resp = client.post("/label", data={"id": "a.jpg", "label": "blocked"})
        assert resp.status_code == 200
        resp = client.post("/label", data={"id": "b.jpg", "label": "clear"})
        assert resp.status_code == 200

    assert (tmp_path / "blocked_signals" / "a.jpg").exists()
    assert (tmp_path / "clear_signals" / "b.jpg").exists()

    csv_path = tmp_path / "labels.csv"
    with csv_path.open() as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3
