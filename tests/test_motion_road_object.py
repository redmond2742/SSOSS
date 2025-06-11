import sys
import pathlib
import unittest
import math
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ssoss.motion_road_object import GPXPoint
from ssoss.static_road_object import Intersection
import geopy


class GPXFactory:
    """Utility to create linked GPXPoint sequences."""

    @staticmethod
    def build(lons, speeds):
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        points = []
        for i, (lon, spd) in enumerate(zip(lons, speeds)):
            ts = (base_time + timedelta(seconds=i * 10)).isoformat()
            points.append(GPXPoint(i, ts, (0.0, lon), spd))
        for i, pt in enumerate(points):
            if i > 0:
                pt.set_prev_gpx_point(points[i - 1])
            if i < len(points) - 1:
                pt.set_next_gpx_point(points[i + 1])
        return points


def create_intersection():
    return Intersection(
        1,
        ("Main", "First"),
        geopy.Point(0.0, 0.0),
        spd=(25, 25, 25, 25),
        bearing=(0, 90, 180, 270),
    )


class TestTimeToApproach(unittest.TestCase):
    def setUp(self):
        self.intersection = create_intersection()

    def test_constant_speed(self):
        pts = GPXFactory.build([-0.0015, -0.001, -0.0005], [10, 10, 10])
        cur = pts[1]
        d = cur.distance_to(self.intersection.get_location()) - self.intersection.get_sd(1)
        expected = d / cur.get_speed()
        self.assertAlmostEqual(cur.t_to_approach_simple(self.intersection, 1), expected, places=5)
        self.assertAlmostEqual(cur.t_to_approach_acc(self.intersection, 1), expected, places=5)

    def test_acceleration(self):
        pts = GPXFactory.build([-0.0015, -0.001, -0.0003], [10, 20, 30])
        cur = pts[1]
        d_sd = cur.distance_to(self.intersection.get_location()) - self.intersection.get_sd(1)
        acc = cur.acceleration()
        v = cur.get_speed()
        if v ** 2 > 4 * acc * d_sd:
            radical = math.sqrt(v ** 2 - 4 * acc * d_sd)
        else:
            radical = 0
        denom = 2 * acc
        if denom == 0 or d_sd <= 0:
            expected = d_sd / v
        else:
            t_pos = (-v + radical) / denom
            t_neg = (-v - radical) / denom
            expected = min(abs(t_neg), abs(t_pos))
        self.assertAlmostEqual(cur.t_to_approach_acc(self.intersection, 1), expected, places=5)


class TestHeuristics(unittest.TestCase):
    def setUp(self):
        self.intersection = create_intersection()

    def test_prev_current_before_next_true(self):
        pts = GPXFactory.build([-0.0015, -0.001, -0.0003], [10, 10, 10])
        cur = pts[1]
        self.assertTrue(cur.h_prev_and_current_before_next(self.intersection, 1))

    def test_prev_current_before_next_false(self):
        pts = GPXFactory.build([-0.0015, -0.001, -0.0008], [10, 10, 10])
        cur = pts[1]
        self.assertFalse(cur.h_prev_and_current_before_next(self.intersection, 1))

    def test_next_less_than_current(self):
        pts = GPXFactory.build([-0.0015, -0.001, -0.0008], [10, 10, 10])
        cur = pts[1]
        self.assertTrue(cur.h_next_less_than_current(self.intersection, 1))

    def test_next_less_than_current_false(self):
        pts = GPXFactory.build([-0.0015, -0.001, -0.0012], [10, 10, 10])
        cur = pts[1]
        self.assertFalse(cur.h_next_less_than_current(self.intersection, 1))


if __name__ == "__main__":
    unittest.main()
