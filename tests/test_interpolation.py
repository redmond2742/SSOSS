import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import unittest
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from geopy.distance import geodesic

from ssoss.interpolation import position_at_time, time_at_distance


class TestInterpolationAccuracy(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        n = 121
        times = [self.base + timedelta(seconds=i) for i in range(n)]

        # ground truth path in meters
        t_arr = np.arange(n)
        x_true = np.linspace(0, 200, n) + 20 * np.sin(t_arr * 0.3)
        y_true = 30 * np.sin(t_arr * 0.15)

        lat0 = 37.0
        lon0 = -122.0
        rad = np.pi / 180
        cos_lat0 = np.cos(lat0 * rad)
        lat_true = lat0 + (y_true / 6378137.0) * 180 / np.pi
        lon_true = lon0 + (x_true / (6378137.0 * cos_lat0)) * 180 / np.pi

        # add noise
        x_noisy = x_true + rng.normal(0, 5, size=n)
        y_noisy = y_true + rng.normal(0, 5, size=n)
        lat_noisy = lat0 + (y_noisy / 6378137.0) * 180 / np.pi
        lon_noisy = lon0 + (x_noisy / (6378137.0 * cos_lat0)) * 180 / np.pi

        self.track = pd.DataFrame({"t": times, "lat": lat_noisy, "lon": lon_noisy})
        self.truth = pd.DataFrame({"t": times, "lat": lat_true, "lon": lon_true})

        # ground truth cumulative distance
        x_t = (lon_true - lon0) * rad * 6378137.0 * cos_lat0
        y_t = (lat_true - lat0) * rad * 6378137.0
        dist = np.hypot(np.diff(x_t), np.diff(y_t))
        self.dist_true = np.insert(np.cumsum(dist), 0, 0)
        self.time_s = t_arr

    def test_position_accuracy(self):
        errs = []
        for frac in np.linspace(0, 1, 200, endpoint=False):
            t_sec = frac * self.time_s[-1]
            when = self.base + timedelta(seconds=float(t_sec))
            lat, lon = position_at_time(self.track, when)
            lat_gt = np.interp(t_sec, self.time_s, self.truth["lat"])
            lon_gt = np.interp(t_sec, self.time_s, self.truth["lon"])
            d = geodesic((lat_gt, lon_gt), (lat, lon)).meters
            errs.append(d)
        self.assertLess(np.percentile(errs, 95), 6.0)

    def test_time_accuracy(self):
        errs = []
        max_d = self.dist_true[-1]
        for frac in np.linspace(0, 1, 200, endpoint=False):
            d = frac * max_d
            ts = time_at_distance(self.track, d)
            t_sec_gt = np.interp(d, self.dist_true, self.time_s)
            ts_gt = self.base + timedelta(seconds=float(t_sec_gt))
            diff = abs((ts - ts_gt).total_seconds())
            errs.append(diff)
        self.assertLess(np.percentile(errs, 95), 3)


if __name__ == "__main__":
    unittest.main()
