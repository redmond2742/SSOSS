import unittest
import pathlib
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd
import geopy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.dynamic_road_object import DynamicRoadObject


class TestGetInfoAtTimestamp(unittest.TestCase):
    def setUp(self):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        pts = [geopy.Point(0, 0), geopy.Point(0, 0.001), geopy.Point(0, 0.002)]
        ts_list = [base + timedelta(seconds=i * 5) for i in range(3)]
        self.df = pd.DataFrame({
            "t": ts_list,
            "geo_point": pts,
            "spd": [10, 12, 14],
            "id": [1, 1, 1],
            "appr_dir": [0, 0, 0],
            "timestamp": [t.timestamp() for t in ts_list],
            "location": pts,
            "distance": [100, 50, 10],
            "bearing": [0, 0, 0],
        })
        self.obj = DynamicRoadObject.__new__(DynamicRoadObject)
        self.obj.gpx_df = self.df

    def test_basic_lookup(self):
        ts = self.df["timestamp"].iloc[1] + 1
        info = self.obj.get_info_at_timestamp(ts)
        self.assertEqual(info[0], 1)
        self.assertEqual(info[1], 0)
        self.assertEqual(info[2], 12)
        self.assertEqual(info[5], self.df["location"].iloc[1])

    def test_out_of_range(self):
        ts = self.df["timestamp"].iloc[-1] + 100
        info = self.obj.get_info_at_timestamp(ts)
        self.assertEqual(info[2], 14)
        self.assertEqual(info[5], self.df["location"].iloc[-1])


if __name__ == "__main__":
    unittest.main()
