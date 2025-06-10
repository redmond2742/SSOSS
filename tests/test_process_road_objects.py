import sys
import pathlib
import unittest
import pandas as pd
import geopy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.process_road_objects import ProcessRoadObjects
from ssoss.motion_road_object import GPXPoint

class TestGetLocationAtTimestamp(unittest.TestCase):
    def test_location_interpolation(self):
        pro = ProcessRoadObjects()
        pro.gpx_listDF = pd.DataFrame({"gpx_pt": [
            GPXPoint(0, "2025-01-01T00:00:00Z", (0.0, 0.0), 0),
            GPXPoint(1, "2025-01-01T00:00:10Z", (0.0, 10.0), 0)
        ]})
        ts = pro.gpx_listDF.iloc[0,0].get_timestamp() + 5
        loc = pro.get_location_at_timestamp(ts)
        self.assertIsInstance(loc, geopy.Point)
        self.assertAlmostEqual(loc.latitude, 0.0)
        self.assertAlmostEqual(loc.longitude, 5.0)

if __name__ == '__main__':
    unittest.main()
