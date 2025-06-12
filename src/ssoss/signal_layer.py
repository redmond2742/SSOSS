import base64
import io
import sys
from datetime import datetime
from pathlib import Path

import click
import gpxpy
import geopandas as gpd
import pandas as pd
from PIL import Image, ExifTags
from shapely.geometry import Point
import folium


# map exif tag numbers to names for convenience
_EXIF_TAGS = {v: k for k, v in ExifTags.TAGS.items()}
_GPS_TAGS = ExifTags.GPSTAGS


def _dms_to_deg(value, ref):
    if not value:
        return None
    deg = value[0][0] / value[0][1]
    min_ = value[1][0] / value[1][1]
    sec = value[2][0] / value[2][1]
    sign = -1 if ref in ["S", "W"] else 1
    return sign * (deg + min_ / 60 + sec / 3600)


def _extract_exif(path: Path):
    """Return (lat, lon, heading, dt) from image exif or None."""
    try:
        with Image.open(path) as img:
            exif = img._getexif() or {}
    except Exception:
        return None

    gps = exif.get(_EXIF_TAGS.get("GPSInfo"))
    if not gps:
        return None
    gps_data = { _GPS_TAGS.get(k): v for k, v in gps.items() if k in _GPS_TAGS }
    lat = _dms_to_deg(gps_data.get("GPSLatitude"), gps_data.get("GPSLatitudeRef"))
    lon = _dms_to_deg(gps_data.get("GPSLongitude"), gps_data.get("GPSLongitudeRef"))
    if lat is None or lon is None:
        return None
    heading = gps_data.get("GPSImgDirection") or gps_data.get("GPSDestBearing")
    if isinstance(heading, tuple):
        heading = heading[0] / heading[1]
    dt_str = exif.get(_EXIF_TAGS.get("DateTimeOriginal")) or exif.get(_EXIF_TAGS.get("DateTime"))
    dt = None
    if dt_str:
        try:
            dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
    return lat, lon, heading, dt


def _extract_gpx(path: Path):
    gpx_path = path.with_suffix(".gpx")
    if not gpx_path.exists():
        return None
    try:
        with gpx_path.open() as f:
            gpx = gpxpy.parse(f)
    except Exception:
        return None
    point = None
    if gpx.waypoints:
        point = gpx.waypoints[0]
    elif gpx.tracks:
        point = gpx.tracks[0].segments[0].points[0]
    if not point:
        return None
    return (
        point.latitude,
        point.longitude,
        getattr(point, "course", None),
        point.time.replace(tzinfo=None) if point.time else None,
    )


def _load_photo_map(csv_path: Path):
    if not csv_path:
        return {}
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return {}
    df = df.set_index("filename")
    return df.to_dict("index")


def _approach_from_heading(heading):
    if heading is None:
        return None
    idx = int(((heading % 360) + 45) // 90) % 4
    return ["NB", "EB", "SB", "WB"][idx]


def _thumb_base64(path: Path, max_size=(200, 200)) -> str:
    with Image.open(path) as im:
        im.thumbnail(max_size)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", optimize=True, quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


@click.command("build-signal-layer")
@click.option("--blocked-folder", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--clear-folder", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--output-dir", type=click.Path(file_okay=False), required=True)
@click.option("--photos-csv", type=click.Path(exists=True, dir_okay=False), help="Optional CSV with photo metadata")
def build_signal_layer(blocked_folder, clear_folder, output_dir, photos_csv):
    """Build a geospatial layer of signal photo locations."""
    blocked = Path(blocked_folder)
    clear = Path(clear_folder)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mapping = _load_photo_map(Path(photos_csv) if photos_csv else None)

    files = [
        *(p for p in blocked.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}),
        *(p for p in clear.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}),
    ]

    records = []
    for path in files:
        info = _extract_exif(path)
        if not info:
            info = _extract_gpx(path)
        if not info and mapping:
            meta = mapping.get(path.name)
            if meta:
                info = (
                    meta.get("lat"),
                    meta.get("lon"),
                    meta.get("heading"),
                    pd.to_datetime(meta.get("capture_dt")) if meta.get("capture_dt") else None,
                )
                intersection_id = meta.get("intersection_id")
            else:
                intersection_id = None
        else:
            intersection_id = None
        if not info or info[0] is None or info[1] is None:
            click.echo(f"Skipping {path}: no location", err=True)
            continue
        lat, lon, heading, dt = info
        visibility = "blocked" if blocked in path.parents else "clear"
        approach = _approach_from_heading(heading)
        records.append(
            {
                "photo_path": str(path),
                "visibility": visibility,
                "intersection_id": intersection_id,
                "approach_leg": approach,
                "heading_deg": heading,
                "capture_dt": dt,
                "geometry": Point(lon, lat),
                "thumbnail": _thumb_base64(path),
            }
        )

    if not records:
        click.echo("No photos found", err=True)
        return

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")

    gpkg_path = out_dir / "signal_visibility.gpkg"
    gdf.to_file(gpkg_path, layer="signals", driver="GPKG")
    gdf.to_file(out_dir / "signal_visibility.geojson", driver="GeoJSON")

    # folium map
    center = [gdf.geometry.y.mean(), gdf.geometry.x.mean()]
    fmap = folium.Map(location=center, zoom_start=18)
    for _, row in gdf.iterrows():
        popup = folium.Popup(f"<img src='{row['thumbnail']}' width='150'><br>{Path(row['photo_path']).name}<br>ID: {row['intersection_id']}", max_width=200)
        if row["visibility"] == "clear":
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color="green",
                fill=True,
                fill_opacity=0.9,
                popup=popup,
            ).add_to(fmap)
        else:
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=folium.Icon(color="red", icon="remove", prefix="fa"),
                popup=popup,
            ).add_to(fmap)

    fmap.save(str(out_dir / "signal_visibility.html"))
    click.echo(f"Saved outputs to {out_dir}")


if __name__ == "__main__":
    build_signal_layer()

