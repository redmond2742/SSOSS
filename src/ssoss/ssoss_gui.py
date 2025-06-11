import argparse
from gooey import Gooey, GooeyParser
from ssoss_cli import *

import process_road_objects
import process_video


@Gooey(program_name="Safe Sightings of Signs and Signals") #  , tabbed_groups=True
def main():
    parser = GooeyParser(
        #argparse.ArgumentParser(
    prog="Safe Sightings of Signs and Signals",
    description="A Python tool to verify visible traffic signs and signals using GPX and Video files")

    gpx_group = parser.add_argument_group(
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
        "Enter Start and End Time (in seconds) for still images from video file"
    )

    # GPX arguments
    gpx_group.add_argument("-so", "--static_object_file",
                           metavar="Static Objects CSV File",
                           help=".csv input file of static road objects",
                           type=argparse.FileType('r'),
                           widget="FileChooser",
                           gooey_options={'wildcard': "Comma separated file (*.csv)|*.csv",
                                         'message': "Select CSV file for Static Objects"})

    gpx_group.add_argument("-gpx", "--gpx_file",
                           metavar="GPX File",
                           help=".gpx file to process",
                           type=argparse.FileType('r'),
                           widget="FileChooser",
                           gooey_options={'wildcard': "GPX file (*.gpx)|*.gpx",
                                        'message': "Select GPX File"})

    # Video file arguments
    video_group.add_argument("-v", "--video_file",
                            metavar="Video File",
                            help="Video file to process",
                            type=argparse.FileType('r'),
                            widget="FileChooser",
                            gooey_options={'wildcard': "All files (*.*)|*.*",
                                        'message': "Select Video File"})


    # extract frames based on start and end time of video
    video_extract_group.add_argument("-fxs", "--frame_extract_start", metavar="A. Start Frame Extract", help="Start extract frames in video (seconds)", type=int, nargs=1)
    video_extract_group.add_argument("-fxe", "--frame_extract_end", metavar="B. End Frame Extract", help="End Extract frames in video (seconds)",
                                    type=int, nargs=1)

    video_sync_group.add_argument("-sf", "--sync_frame", metavar="1. Sync Frame", help="Sync Frame number for video. Sync with timestamp also", type=int)
    video_sync_group.add_argument("-st", "--sync_timestamp", metavar="2. Sync Timestamp", help="2. Sync Timestamp ('2022-10-24T14:21:54.988Z') for video. Sync with frame number also", type=str)

    video_sync_group.add_argument("-label", "--label", metavar="Overlay Image Label", help="Include descriptive label on bottom of image", action="store_true", default=True)
    video_sync_group.add_argument("-gif", "--gif", metavar="Create Animated GIF", help="Generate GIF of Sight Distance", action="store_true", default=False)

    # GIF options available only through CLI; defaults are used here

    args = parser.parse_args()

    sync_input = ("", "")
    frames = ("", "")
    if args.sync_frame and args.sync_timestamp:
        sync_input = (args.sync_frame, args.sync_timestamp)
    if args.frame_extract_start and args.frame_extract_end:
        frames = (args.frame_extract_start[0], args.frame_extract_end[0])

    lb = args.label
    gif = args.gif
    cleanup = True
    overwrite = False
    extra_out = (lb, gif, cleanup, overwrite)

    args_static_obj_gpx_video(generic_so_file = args.static_object_file,
                              gpx_file = args.gpx_file,
                              video_file = args.video_file,
                              vid_sync = sync_input,
                              frame_extract = frames,
                              extra_out = extra_out
                              )


if __name__ == "__main__":
    main()




