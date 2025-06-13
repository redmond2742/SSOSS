# Tests for ssoss_cli command line interface
import sys
import pathlib
import pytest
from unittest import mock

root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src" / "ssoss"))
sys.path.insert(0, str(root / "src"))

import ssoss.ssoss_cli as ssoss_cli


@pytest.fixture
def run_cli(monkeypatch):
    """Run ``ssoss_cli.main`` with given arguments and capture the call to
    ``args_static_obj_gpx_video``."""
    def _run(args):
        called = {}

        def fake(**kwargs):
            called.update(kwargs)

        monkeypatch.setattr(ssoss_cli, "args_static_obj_gpx_video", fake)
        monkeypatch.setattr(sys, "argv", ["ssoss"] + args)
        ssoss_cli.main()
        return called

    return _run


def test_parser_accepts_basic_args(run_cli, tmp_path):
    so = tmp_path / "so.csv"
    gpx = tmp_path / "track.gpx"
    so.write_text("id\n")
    gpx.write_text("<gpx></gpx>")

    result = run_cli(["--static_object_file", str(so), "--gpx_file", str(gpx)])

    assert pathlib.Path(result["generic_so_file"].name) == so
    assert pathlib.Path(result["gpx_file"].name) == gpx
    assert result["video_file"] is None


def test_parser_rejects_invalid_int(tmp_path):
    vid = tmp_path / "video.mov"
    vid.write_text("data")
    with pytest.raises(SystemExit):
        sys.argv = ["ssoss", "--video_file", str(vid), "--frame_extract_start", "bad"]
        ssoss_cli.main()


def test_dispatch_sync_calls(monkeypatch, tmp_path):
    so = tmp_path / "so.csv"
    gpx = tmp_path / "track.gpx"
    vid = tmp_path / "video.mov"
    so.write_text("1,2,3,4,5,6,7\n")
    gpx.write_text("<gpx></gpx>")
    vid.write_text("data")

    pr_instance = mock.MagicMock()
    pr_instance.get_static_object_type.return_value = "intersection"
    pr_instance.intersection_checks.return_value = ["sig"]
    pr_cls = mock.MagicMock(return_value=pr_instance)

    pv_instance = mock.MagicMock()
    pv_cls = mock.MagicMock(return_value=pv_instance)

    monkeypatch.setattr(ssoss_cli.process_road_objects, "ProcessRoadObjects", pr_cls)
    monkeypatch.setattr(ssoss_cli.process_video, "ProcessVideo", pv_cls)

    with so.open("r") as so_f, gpx.open("r") as gpx_f, vid.open("r") as vid_f:
        ssoss_cli.args_static_obj_gpx_video(
            generic_so_file=so_f,
            gpx_file=gpx_f,
            video_file=vid_f,
            vid_sync=(1, "ts"),
            frame_extract=("", ""),
            extra_out=(True, False),
        )

    pv_instance.sync.assert_called_once_with(1, "ts", autosync=False)
    pv_instance.extract_sightings.assert_called_once_with(
        ["sig"], pr_instance, label_img=True, gen_gif=False
    )


def test_dispatch_extract_frames(monkeypatch, tmp_path):
    vid = tmp_path / "video.mov"
    vid.write_text("data")

    pv_instance = mock.MagicMock()
    pv_cls = mock.MagicMock(return_value=pv_instance)
    monkeypatch.setattr(ssoss_cli.process_video, "ProcessVideo", pv_cls)

    with vid.open("r") as vid_f:
        ssoss_cli.args_static_obj_gpx_video(
            video_file=vid_f,
            vid_sync=("", ""),
            frame_extract=(1, 2),
            extra_out=(False, False),
        )

    pv_instance.extract_frames_between.assert_called_once_with(1, 2)


def test_autosync_uses_filename(run_cli, tmp_path):
    vid = tmp_path / "09-15-2023--14-12-24.123-UTC.mov"
    vid.write_text("data")

    result = run_cli(["--video_file", str(vid), "--autosync"])

    assert result["vid_sync"][0] == 1
    assert result["vid_sync"][1].startswith("2023-09-15T14:12:24.123000")

