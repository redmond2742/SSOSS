import sys
import pathlib
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.process_road_objects import ProcessRoadObjects
from ssoss.motion_road_object import GPXPoint
import pandas as pd


class TestLocationInterpolation(unittest.TestCase):
    def setUp(self):
        p0 = GPXPoint(0, datetime.fromtimestamp(0, tz=timezone.utc).isoformat(), (0.0, 0.0), 0)
        p1 = GPXPoint(1, datetime.fromtimestamp(10, tz=timezone.utc).isoformat(), (0.0, 1.0), 0)
        self.proc = ProcessRoadObjects()
        self.proc.gpx_listDF = pd.DataFrame({"gpx_pt": [p0, p1]})

    def test_midpoint_interpolation(self):
        ts = 5.0
        location = self.proc.get_location_at_timestamp(ts)
        self.assertIsNotNone(location)
        self.assertAlmostEqual(location.latitude, 0.0, places=6)
        self.assertAlmostEqual(location.longitude, 0.5, places=6)


if __name__ == "__main__":
    unittest.main()
