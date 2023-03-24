import argparse
import process_road_objects
import process_video


def main():
    parser = argparse.ArgumentParser(
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
    gpx_group.add_argument("-so", "--static_objects",
                           metavar="Static Objects CSV File",
                           help=".csv input file of static road objects",
                           type=argparse.FileType('r'),
                           )

    gpx_group.add_argument("-gpx", "--gpx_file",
                           metavar="GPX File",
                           help=".gpx file to process",
                           type=argparse.FileType('r')
                           )

    # Video file arguments
    video_group.add_argument("-v", "--video_file",
                            metavar="Video File",
                            help="Video file to process",
                            type=argparse.FileType('r')
                            )



    # extract frames based on video frame and timestamp

    # extract frames based on start and end time of video
    video_extract_group.add_argument("-fxs", "--frame_extract_start", help="Start extract frames in video (seconds)", type=int, nargs=1)
    video_extract_group.add_argument("-fxe", "--frame_extract_end", help="End Extract frames in video (seconds)",
                                    type=int, nargs=1)

    video_sync_group.add_argument("-sf", "--sync_frame", help="Sync Frame number for video. Sync with timestamp also", type=int)
    video_sync_group.add_argument("-st", "--sync_timestamp", help="2. Sync Timestamp ('2022-10-24T14:21:54.988Z') for video. Sync with frame number also", type=str)

    video_sync_group.add_argument("--labelbox", help="Include descriptive label on bottom of image", action="store_false")
    video_sync_group.add_argument("--gif", help="Generate GIF of Sight Distance", action="store_false")

    args = parser.parse_args()

    if args.gpx_file and args.static_objects:
        project = process_road_objects.ProcessRoadObjects(args.gpx_file.name, args.static_objects.name)
        sightings = project.intersection_checks()

    if args.video_file is not None:
        video = process_video.ProcessVideo(args.video_file.name)
        if args.sync_frame and args.sync_timestamp:
            print(args.sync_frame)
            print(args.sync_timestamp)
            video.sync(int(args.sync_frame), args.sync_timestamp)
            if args.static_objects and args.gpx_file:
                video.extract_sightings(sightings, project, gen_gif=args.gif)
        elif args.frame_extract_start and args.frame_extract_end:
            video.extract_frames_between(args.frame_extract_start[0], args.frame_extract_end[0])



if __name__ == "__main__":
    main()




