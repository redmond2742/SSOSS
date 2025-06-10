import unittest
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.process_video import ProcessVideo
from ssoss.process_road_objects import ProcessRoadObjects


class TestHrMinSec(unittest.TestCase):
    def test_seconds_only(self):
        self.assertEqual(ProcessVideo.hr_min_sec(50), "50 seconds")
        self.assertEqual(ProcessRoadObjects.hr_min_sec(50), "50 seconds")

    def test_minutes_seconds(self):
        self.assertEqual(
            ProcessVideo.hr_min_sec(125.8),
            "02:05.80 (MM:SS.ss)"
        )
        self.assertEqual(
            ProcessRoadObjects.hr_min_sec(125.8),
            "02:05.80 (MM:SS.ss)"
        )

    def test_hours_minutes_seconds(self):
        self.assertEqual(
            ProcessVideo.hr_min_sec(3661.2),
            "01:01:01.20 (HH:MM:SS.ss)"
        )
        self.assertEqual(
            ProcessRoadObjects.hr_min_sec(3661.2),
            "01:01:01.20 (HH:MM:SS.ss)"
        )


if __name__ == "__main__":
    unittest.main()
