import argparse
import re


from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
# When executed as part of the ``ssoss`` package, ``__package__`` will be set
# and the relative imports below work as expected.  Running the module as a
# stand-alone script (e.g. ``python ssoss_cli.py``) leaves ``__package__`` empty
# which causes relative imports to fail.  Handle both execution modes here.
if __package__ in {None, ""}:
    import process_road_objects
    import process_video
else:
    from . import process_road_objects
    from . import process_video




def _timestamp_from_filename(path: str) -> str:
    """Extract ISO 8601 timestamp from ``path``.

    The filename should contain a timestamp formatted as
    ``MM-DD-YYYY--HH-MM-SS.sss-ZZZ`` where ``ZZZ`` is a timezone
    abbreviation such as ``UTC`` or ``PDT``. The time itself is not shifted
    based on the timezone; the offset is simply attached to the parsed
    timestamp.
    """

    base = Path(path).stem
    m = re.search(
        r"(?P<ts>\d{2}-\d{2}-\d{4}--\d{2}-\d{2}-\d{2}\.\d+)-(?P<zone>[A-Za-z]+)$",
        base,
    )
    if not m:
        raise ValueError("No timestamp found in video filename")

    ts_str = m.group("ts")
    zone = m.group("zone")

    dt = datetime.strptime(ts_str, "%m-%d-%Y--%H-%M-%S.%f")
    zone = zone.upper()
    offset_map = {
        "UTC": 0,
        "PST": -8,
        "PDT": -7,
        "MST": -7,
        "MDT": -6,
        "CST": -6,
        "CDT": -5,
        "EST": -5,
        "EDT": -4,
    }
    hours = offset_map.get(zone, 0)
    #tz = timezone(timedelta(hours=0))
    #dt = dt.replace(tzinfo=tz)
    print(dt)
    print(dt.isoformat())
    return dt.isoformat()

def cli_summary(descriptions, project, video):
    """Print a summary of extracted images and processing stats."""

    width = 70
    title = "CLI SUMMARY"
    symbol = "="

    num_images = len(descriptions)
    gpx_dur = project.get_end_timestamp() - project.get_start_timestamp()
    vid_dur = video.get_duration()

    avg_gpx = gpx_dur / num_images if num_images else 0
    avg_vid = vid_dur / num_images if num_images else 0

    intersections = {}
    for desc in descriptions:
        prefix = desc.split("-", 1)[0]
        parts = prefix.split(".")
        if len(parts) >= 2:
            int_id = int(parts[0])
            bearing = int(parts[1])
            intersections.setdefault(int_id, set()).add(bearing)

    intersection_lines = []
    for int_id in sorted(intersections):
        count = len(intersections[int_id])
        pct = count / 4 * 100
        intersection_lines.append(
            f"# Intersection {int_id}: {count}/4 approaches ({pct:.1f}%)"
        )

    multiplier = (18 * 60 / avg_vid) if avg_vid else 0

    summary = f"""
{symbol * width}
{" " * (int(width/2)-int(len(title)/2))}{title}
{symbol * width}
# Number of Images: {num_images}
# Number of Intersections: {len(intersections)}
{chr(10).join(intersection_lines)}
# Avg Time per Image (GPX): {project.hr_min_sec(avg_gpx)}
# Avg Time per Image (Video): {project.hr_min_sec(avg_vid)}
# SSOSS Multiplier: {multiplier:.1f}X compared to field check
{symbol * width}
"""
    print(summary)



def args_static_obj_gpx_video(
    generic_so_file="",
    gpx_file="",
    video_file="",
    vid_sync=("", ""),
    frame_extract=("", ""),
    extra_out=(True, False, True, False),
    autosync=False,
):

    sightings = ""
    if generic_so_file and gpx_file:
        project = process_road_objects.ProcessRoadObjects(
            gpx_filestring=gpx_file.name,
            generic_static_object_filestring=generic_so_file.name,
        )
        if project.get_static_object_type() == "intersection":
            sightings = project.intersection_checks()
        elif project.get_static_object_type() == "generic static object":
            sightings = project.generic_so_checks()

    if generic_so_file:
        process_road_objects.ProcessRoadObjects(
            generic_static_object_filestring=generic_so_file.name
        )
    elif gpx_file:
        process_road_objects.ProcessRoadObjects(gpx_filestring=gpx_file.name)


    # ``extra_out`` may be shorter than four elements in tests
    defaults = (True, False, True, False)
    supplied_len = len(extra_out)
    extra = list(extra_out) + list(defaults[supplied_len:])
    extra_out = tuple(extra[:4])

    if video_file:
        video = process_video.ProcessVideo(video_file.name)
        if vid_sync[0] and vid_sync[1]:
            video.sync(int(vid_sync[0]), vid_sync[1], autosync=autosync)
            if sightings and project.get_static_object_type() == "intersection":
                print("extracting traffic signal sightings")
                kwargs = {"label_img": extra_out[0], "gen_gif": extra_out[1]}
                if supplied_len > 2:
                    kwargs["cleanup"] = extra_out[2]
                if supplied_len > 3:
                    kwargs["overwrite"] = extra_out[3]
                desc_list = video.extract_sightings(sightings, project, **kwargs)
                cli_summary(desc_list, project, video)
            if sightings and project.get_static_object_type() == "generic static object":
                print("extracting generic static object sightings")
                kwargs = {"label_img": extra_out[0], "gen_gif": extra_out[1]}
                if supplied_len > 2:
                    kwargs["cleanup"] = extra_out[2]
                if supplied_len > 3:
                    kwargs["overwrite"] = extra_out[3]
                desc_list = video.extract_generic_so_sightings(sightings, project, **kwargs)
                cli_summary(desc_list, project, video)
        elif frame_extract[0] and frame_extract[1]:
            print("extracting frames...")
            video.extract_frames_between(frame_extract[0], frame_extract[1])


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="Safe Sightings of Signs and Signals",
        description="Software to help verify visible traffic signs and signals using GPX and Video files",
    )

    so_and_gpx_group = parser.add_argument_group(
        "Static Objects and GPX Input",
        "Select Static Object CSV input File and GPX File"
    )
    video_group = parser.add_argument_group(
        "Video Files and Options",
        "Select Video and Extract Frames or Sync Video to GPX"
    )
    video_sync_group = parser.add_argument_group(
        "Sync Video at Specified Frame and Time",
        "Enter the frame number that corresponds to a timestamp"
    )
    video_extract_group = parser.add_argument_group(
        "Extract Frames from Video File",
        "Enter Start and End Time (in seconds) for still images from video file",

    )

    # Static Object & GPX arguments
    so_and_gpx_group.add_argument(
        "-so",
        "--static_object_file",
        metavar="Static Object File",
        help=".csv file to process of static road objects (Intersections, signs, etc.)",
        type=argparse.FileType("r"),
    )


    so_and_gpx_group.add_argument(
        "-gpx",
        "--gpx_file",
        metavar="GPX File",
        help=".gpx file to process",
        type=argparse.FileType("r"),
    )

    # Video file arguments
    video_group.add_argument(
        "-v",
        "--video_file",
        metavar="Video File",
        help="Video file to process",
        type=argparse.FileType("r"),
    )

    # extract frames based on start and end time of video
    video_extract_group.add_argument(
        "-fxs",
        "--frame_extract_start",
        help="Start extract frames in video (seconds)",
        type=int,
        nargs=1,
    )
    video_extract_group.add_argument(
        "-fxe",
        "--frame_extract_end",
        help="End Extract frames in video (seconds)",
        type=int,
        nargs=1,
    )

    video_sync_group.add_argument(
        "-sf",
        "--sync_frame",
        help="Sync Frame number for video. Sync with timestamp also",
        type=int,
    )
    video_sync_group.add_argument(
        "-st",
        "--sync_timestamp",
        help="2. Sync Timestamp ('2022-10-24T14:21:54.988Z') for video. Sync with frame number also",
        type=str,
    )
    video_sync_group.add_argument(
        "--autosync",
        action="store_true",
        help="Sync using timestamp embedded in video filename",
    )

    video_sync_group.add_argument(
        "--label",
        help="Include descriptive label on bottom of image",
        action="store_true",
    )
    video_sync_group.add_argument(
        "--gif",
        help="Generate GIF of Sight Distance",
        action="store_true",
    )
    video_sync_group.add_argument(
        "--bbox",
        help="Add bounding box around traffic signals",
        action="store_true",
    )
    video_sync_group.add_argument(
        "--no-gif-cleanup",
        dest="gif_cleanup",
        help="Keep extracted GIF frames after assembly",
        action="store_false",
        default=True,
    )
    video_sync_group.add_argument(
        "--gif-overwrite",
        dest="gif_overwrite",
        help="Overwrite existing GIF files",
        action="store_true",
        default=False,
    )

    # process args depending on filled in values
    args = parser.parse_args(argv)

    sync_input = ("", "")
    frames = ("", "")
    if args.autosync:
        if not args.video_file:
            parser.error("--autosync requires --video_file")
        try:
            ts = _timestamp_from_filename(args.video_file.name)
            sync_input = (1, ts)
        except ValueError as e:
            parser.error(str(e))
    elif args.sync_frame and args.sync_timestamp:
        sync_input = (args.sync_frame, args.sync_timestamp)
    if args.frame_extract_start and args.frame_extract_end:
        frames = (args.frame_extract_start[0], args.frame_extract_end[0])

    lb = gif = bbox = False
    if args.label:
        lb = True
    if args.gif:
        gif = True
    if args.bbox:
        bbox = True
    cleanup = args.gif_cleanup
    overwrite = args.gif_overwrite
    lb_gif_flags = (lb, gif, cleanup, overwrite)


    # process args
    args_static_obj_gpx_video(generic_so_file = args.static_object_file,
                              gpx_file = args.gpx_file,
                              video_file = args.video_file,
                              vid_sync = sync_input,
                              frame_extract = frames,
                              extra_out = lb_gif_flags,
                              autosync = args.autosync
                              )


if __name__ == "__main__":
    main()
