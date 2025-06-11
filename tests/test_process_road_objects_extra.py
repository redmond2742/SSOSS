import sys
import pathlib
import unittest
import tempfile
import csv
import pandas as pd
import geopy
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.process_road_objects import ProcessRoadObjects
from ssoss.static_road_object import GenericStaticObject, Intersection
from ssoss.motion_road_object import GPXPoint


class GPXFixture:
    """Helper to generate simple GPX data for tests."""

    @staticmethod
    def create_points():
        return pd.DataFrame({"gpx_pt": [
            GPXPoint(0, "2025-01-01T00:00:00Z", (0.0, 0.0), 0),
            GPXPoint(1, "2025-01-01T00:00:10Z", (0.0, 0.001), 1),
            GPXPoint(2, "2025-01-01T00:00:20Z", (0.0, 0.002), 1),
        ]})


class TestSpeedCalc(unittest.TestCase):
    def test_normal_speed(self):
        p1 = geopy.Point(0.0, 0.0)
        p2 = geopy.Point(0.0, 0.001)
        t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=10)
        expected = geopy.distance.distance(p1, p2).meters / 10
        result = ProcessRoadObjects.speed_calc(p1, p2, t1, t2)
        self.assertAlmostEqual(result, expected, places=5)

    def test_zero_time(self):
        p = geopy.Point(0.0, 0.0)
        t = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(ProcessRoadObjects.speed_calc(p, p, t, t), 0.0)

    def test_excessive_speed_returns_zero(self):
        p1 = geopy.Point(0.0, 0.0)
        p2 = geopy.Point(0.1, 0.1)  # far enough for high speed
        t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=1)
        self.assertEqual(ProcessRoadObjects.speed_calc(p1, p2, t1, t2), 0.0)


class TestCSVLoading(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_load_generic_so_csv(self):
        path = pathlib.Path(self.tmpdir.name, "generic.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "street", "lat", "lon", "bearing", "desc", "dist"])
            writer.writerow([1, "Main", 0.0, 0.0, "NB", "Stop", 50])

        pro = ProcessRoadObjects()
        pro.load_generic_so_csv(str(path))
        df = pro.generic_so_listDF
        self.assertEqual(len(df), 1)
        obj = df.iloc[0, 1]
        self.assertIsInstance(obj, GenericStaticObject)
        self.assertEqual(obj.get_name(), "Main")
        self.assertEqual(obj.get_bearing(), 0)

    def test_load_intersection_csv(self):
        path = pathlib.Path(self.tmpdir.name, "intersection.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "n1", "n2", "lat", "lon", "sn", "se", "ss", "sw",
                "bn", "be", "bs", "bw",
            ])
            writer.writerow([1, "Main", "First", 0.0, 0.0,
                             25, 25, 25, 25,
                             0, 90, 180, 270])

        pro = ProcessRoadObjects()
        df = pro.load_intersection_csv(str(path))
        self.assertEqual(len(df), 1)
        obj = df.iloc[0, 1]
        self.assertIsInstance(obj, Intersection)
        self.assertEqual(obj.get_name(), "Main+First")
        self.assertEqual(obj.get_sd(0), 215)


class TestTimestampQueries(unittest.TestCase):
    def setUp(self):
        self.pro = ProcessRoadObjects()
        self.pro.gpx_listDF = GPXFixture.create_points()

    def test_get_speed_at_timestamp_between_points(self):
        ts = self.pro.gpx_listDF.iloc[0, 0].get_timestamp() + 5
        spd = self.pro.get_speed_at_timestamp(ts)
        s0 = self.pro.gpx_listDF.iloc[0, 0].get_speed()
        s1 = self.pro.gpx_listDF.iloc[1, 0].get_speed()
        self.assertAlmostEqual(spd, (s0 + s1) / 2)

    def test_get_speed_at_timestamp_out_of_range(self):
        ts = self.pro.gpx_listDF.iloc[-1, 0].get_timestamp() + 10
        self.assertIsNone(self.pro.get_speed_at_timestamp(ts))

    def test_get_location_at_timestamp_out_of_range(self):
        ts = self.pro.gpx_listDF.iloc[-1, 0].get_timestamp() + 10
        self.assertIsNone(self.pro.get_location_at_timestamp(ts))


class TestDescriptionFormatting(unittest.TestCase):
    def setUp(self):
        self.pro = ProcessRoadObjects()
        generic_obj = GenericStaticObject(1, "Main", geopy.Point(0, 0), "NB", "Stop", 50)
        self.pro.generic_so_listDF = pd.DataFrame({"id": [1], "generic_so_obj": [generic_obj]})

        inter_obj = Intersection(
            1,
            ("Main", "First"),
            geopy.Point(0, 0),
            spd=(25, 25, 25, 25),
            bearing=(0, 90, 180, 270),
        )
        self.pro.intersection_listDF = pd.DataFrame({"id": [1], "intersection_obj": [inter_obj]})

    def test_generic_so_description_filename(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()
        desc = self.pro.generic_so_description(1, 40, ts)
        self.assertTrue(desc.startswith("1.50-Main-Stop-"))

    def test_intersection_frame_description_label(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()
        label = self.pro.intersection_frame_description(1, 0, 30, ts, desc_type="label")
        self.assertIn("NB approach", label)
        self.assertIn("Main and First", label)


if __name__ == "__main__":
    unittest.main()
