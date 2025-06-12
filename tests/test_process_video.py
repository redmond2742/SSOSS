import sys
import pathlib
import unittest
import tempfile
import os
import cv2
import numpy as np
from PIL import Image
import piexif
import geopy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.process_video import ProcessVideo

class DummyProject:
    def get_location_at_timestamp(self, ts):
        return geopy.Point(1.0, 2.0)

class VideoFixture:
    @staticmethod
    def create_video(path, fps=10, frames=20):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(path), fourcc, fps, (64, 64))
        for i in range(frames):
            frame = np.full((64, 64, 3), i, dtype=np.uint8)
            out.write(frame)
        out.release()

class TestProcessVideo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.video_path = pathlib.Path(self.tmp.name, "test.mp4")
        VideoFixture.create_video(self.video_path)
        self.pv = ProcessVideo(str(self.video_path))
        self.pv.set_start_utc(100)
        self.project = DummyProject()

    def test_create_pic_list_from_zip(self):
        desc_ts = [
            ("a", 101),
            ("b", 101.05),
            ("c", 101.9),
            ("d", 102.5),
        ]
        desc, frames, ts = self.pv.create_pic_list_from_zip(desc_ts)
        self.assertEqual(desc, ["a", "c"])
        self.assertEqual(frames, [10, 19])
        self.assertEqual(ts, [101, 101.9])

    def test_sync_sets_start_time_and_logs(self):
        self.pv.sync(10, 110.0)
        expected_start = 110.0 - 10 / self.pv.fps
        self.assertAlmostEqual(self.pv.get_start_timestamp(), expected_start)
        sync_file = pathlib.Path(self.pv.video_dir, "out", "sync.txt")
        with open(sync_file) as f:
            line = f.read().strip()
        self.assertEqual(line, f"{self.pv.video_filepath.stem},10,110.0")

    def test_sync_does_not_duplicate_lines(self):
        self.pv.sync(10, 110.0)
        self.pv.sync(10, 110.0)
        sync_file = pathlib.Path(self.pv.video_dir, "out", "sync.txt")
        with open(sync_file) as f:
            lines = [l.strip() for l in f]
        self.assertEqual(lines, [f"{self.pv.video_filepath.stem},10,110.0"])

    def _check_gps(self, image_path):
        exif = piexif.load(str(image_path))
        gps = exif.get("GPS", {})
        self.assertEqual(gps.get(piexif.GPSIFD.GPSLatitudeRef), b"N")
        self.assertEqual(gps.get(piexif.GPSIFD.GPSLongitudeRef), b"E")

    def test_extract_functions_save_with_gps(self):
        desc_ts = [("pic", 101)]
        self.pv.extract_sightings(desc_ts, self.project, label_img=False, gen_gif=False)
        file1 = pathlib.Path(self.tmp.name, "out", self.video_path.stem, "signal_sightings", "pic.jpg")
        self.assertTrue(file1.exists())
        self._check_gps(file1)

        self.pv.extract_generic_so_sightings(desc_ts, self.project, label_img=False, gen_gif=False)
        file2 = pathlib.Path(self.tmp.name, "out", self.video_path.stem, "generic_static_object_sightings", "pic.jpg")
        self.assertTrue(file2.exists())
        self._check_gps(file2)

if __name__ == "__main__":
    unittest.main()
