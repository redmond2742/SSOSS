import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from geographiclib.geodesic import Geodesic


def _prep_track(track_df: pd.DataFrame):
    if "t" in track_df.columns:
        t = pd.to_datetime(track_df["t"], utc=True)
    elif "time" in track_df.columns:
        t = pd.to_datetime(track_df["time"], utc=True)
    elif "timestamp" in track_df.columns:
        t = pd.to_datetime(track_df["timestamp"], unit="s", utc=True)
    else:
        raise ValueError("track_df must contain a time column (t/time/timestamp)")

    if "lat" in track_df.columns and "lon" in track_df.columns:
        lat = track_df["lat"].astype(float)
        lon = track_df["lon"].astype(float)
    elif "latitude" in track_df.columns and "longitude" in track_df.columns:
        lat = track_df["latitude"].astype(float)
        lon = track_df["longitude"].astype(float)
    else:
        raise ValueError("track_df must contain lat/lon columns")

    df = pd.DataFrame({"t": t, "lat": lat, "lon": lon})
    df.sort_values("t", inplace=True)
    df.reset_index(drop=True, inplace=True)

    df["lat"] = df["lat"].rolling(window=5, center=True, min_periods=1).mean()
    df["lon"] = df["lon"].rolling(window=5, center=True, min_periods=1).mean()

    dist = [0.0]
    for i in range(1, len(df)):
        p0 = df.iloc[i - 1]
        p1 = df.iloc[i]
        d = Geodesic.WGS84.Inverse(p0.lat, p0.lon, p1.lat, p1.lon)["s12"]
        dist.append(d)
    df["distance_m"] = np.cumsum(dist)
    df["time_s"] = (df["t"] - df["t"].iloc[0]).dt.total_seconds()
    return df, df["t"].iloc[0]


def position_at_time(track_df: pd.DataFrame, when: datetime) -> tuple[float, float]:
    df, t0 = _prep_track(track_df)
    ts = pd.to_datetime(when, utc=True)
    t_sec = (ts - t0).total_seconds()
    if t_sec < df["time_s"].iloc[0] or t_sec > df["time_s"].iloc[-1]:
        raise ValueError("time outside track range")

    idx = np.searchsorted(df["time_s"], t_sec) - 1
    idx = np.clip(idx, 0, len(df) - 2)
    t0s = df["time_s"].iloc[idx]
    t1s = df["time_s"].iloc[idx + 1]
    ratio = (t_sec - t0s) / (t1s - t0s)
    p0 = df.iloc[idx]
    p1 = df.iloc[idx + 1]
    inv = Geodesic.WGS84.Inverse(p0.lat, p0.lon, p1.lat, p1.lon)
    pt = Geodesic.WGS84.Direct(p0.lat, p0.lon, inv["azi1"], inv["s12"] * ratio)
    return pt["lat2"], pt["lon2"]


def time_at_distance(track_df: pd.DataFrame, distance_m: float) -> datetime:
    df, t0 = _prep_track(track_df)
    if distance_m < 0 or distance_m > df["distance_m"].iloc[-1]:
        raise ValueError("distance outside track range")

    idx = np.searchsorted(df["distance_m"], distance_m) - 1
    idx = np.clip(idx, 0, len(df) - 2)
    d0 = df["distance_m"].iloc[idx]
    d1 = df["distance_m"].iloc[idx + 1]
    ratio = (distance_m - d0) / (d1 - d0)
    t0s = df["time_s"].iloc[idx]
    t1s = df["time_s"].iloc[idx + 1]
    t_sec = t0s + ratio * (t1s - t0s)
    return t0 + timedelta(seconds=float(t_sec))
