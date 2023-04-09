import argparse
import process_road_objects
import process_video


def args_static_obj_gpx_video(static_obj="", gpx_file="", video_file="",
                              vid_sync=("",""), frame_extract=("",""), extra_out=(True, False)):
    sightings = ""
    if static_obj and gpx_file:
        project = process_road_objects.ProcessRoadObjects(gpx_file.name, static_obj.name)
        sightings = project.intersection_checks()
    elif static_obj:
        process_road_objects.ProcessRoadObjects("", static_obj.name)
    elif gpx_file:
        process_road_objects.ProcessRoadObjects(gpx_file.name, "")

    if video_file:
        video = process_video.ProcessVideo(video_file.name)
        if vid_sync[0] and vid_sync[1]:
            video.sync(int(vid_sync[0]), vid_sync[1])
            if sightings:
                video.extract_sightings(sightings, project, label_img=extra_out[0], gen_gif=extra_out[1])
        elif frame_extract[0] and frame_extract[1]:
            print("extracting frames...")
            video.extract_frames_between(frame_extract[0], frame_extract[1])


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

    # extract frames based on start and end time of video
    video_extract_group.add_argument("-fxs", "--frame_extract_start", help="Start extract frames in video (seconds)", type=int, nargs=1)
    video_extract_group.add_argument("-fxe", "--frame_extract_end", help="End Extract frames in video (seconds)",
                                    type=int, nargs=1)

    video_sync_group.add_argument("-sf", "--sync_frame", help="Sync Frame number for video. Sync with timestamp also", type=int)
    video_sync_group.add_argument("-st", "--sync_timestamp", help="2. Sync Timestamp ('2022-10-24T14:21:54.988Z') for video. Sync with frame number also", type=str)

    video_sync_group.add_argument("--labelbox", help="Include descriptive label on bottom of image", action="store_true")
    video_sync_group.add_argument("--gif", help="Generate GIF of Sight Distance", action="store_true")


    # process args depending on filled in values
    args = parser.parse_args()

    sync_input = ("", "")
    frames = ("", "")
    if args.sync_frame and args.sync_timestamp:
        sync_input = (args.sync_frame, args.sync_timestamp)
    if args.frame_extract_start and args.frame_extract_end:
        frames = (args.frame_extract_start[0], args.frame_extract_end[0])
    if args.labelbox and args.gif:
        label_and_gif = (args.labelbox, args.gif)
    elif args.labelbox:
        label_and_gif = (args.labelbox, False)
    elif args.gif:
        label_and_gif = (False, args.gif)
    else:
        label_and_gif = (True, False)

    args_static_obj_gpx_video(args.static_objects, args.gpx_file,
                              args.video_file,
                              sync_input, frames, label_and_gif)


if __name__ == "__main__":
    main()