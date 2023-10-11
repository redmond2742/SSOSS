import argparse
import process_road_objects
import process_video


def args_static_obj_gpx_video(generic_so_file = "", gpx_file="", video_file="",
                              vid_sync=("",""), frame_extract=("",""), extra_out=(True, False)):
    
    sightings = ""
    if generic_so_file and gpx_file:
        project = process_road_objects.ProcessRoadObjects(gpx_filestring = gpx_file.name, generic_static_object_filestring = generic_so_file.name)
        if project.get_static_object_type() == "intersection":
            sightings = project.intersection_checks()
        elif project.get_static_object_type() == "generic static object":
            sightings = project.generic_so_checks()
        ic(sightings)
   
    if generic_so_file:
        process_road_objects.ProcessRoadObjects(generic_static_object_filestring = generic_so_file.name)
    elif gpx_file:
        process_road_objects.ProcessRoadObjects(gpx_filestring = gpx_file.name)


    if video_file:
        video = process_video.ProcessVideo(video_file.name)
        if vid_sync[0] and vid_sync[1]:
            video.sync(int(vid_sync[0]), vid_sync[1])
            if sightings and project.get_static_object_type() == "intersection":
                print('extracting traffic signal sightings')
                video.extract_sightings(sightings, project, label_img=extra_out[0], gen_gif=extra_out[1])
            if sightings and project.get_static_object_type() == "generic static object":
                print('extracting generic static object sightings')
                video.extract_generic_so_sightings(sightings, project, label_img=extra_out[0], gen_gif=extra_out[1])
        elif frame_extract[0] and frame_extract[1]:
            print("extracting frames...")
            video.extract_frames_between(frame_extract[0], frame_extract[1])


def main():
    parser = argparse.ArgumentParser(
    prog="Safe Sightings of Signs and Signals",
    description="A automated tool to verify visible traffic signs and signals using GPX and Video files")

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
        "Enter Start and End Time (in seconds) for still images from video file"
    )

    # Static Object & GPX arguments                            )
    so_and_gpx_group.add_argument("-so", "--static_object_file",
                           metavar="Static Object File",
                           help=".csv file to process of static road objects (Intersections, signs, etc.)",
                           type=argparse.FileType('r')
    )
    
    so_and_gpx_group.add_argument("-gpx", "--gpx_file",
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

    video_sync_group.add_argument("--label", help="Include descriptive label on bottom of image", action="store_true")
    video_sync_group.add_argument("--gif", help="Generate GIF of Sight Distance", action="store_true")
    video_sync_group.add_argument("--bbox", help="Add bounding box around traffic signals", action="store_true")

    # process args depending on filled in values
    args = parser.parse_args()

    sync_input = ("", "")
    frames = ("", "")
    if args.sync_frame and args.sync_timestamp:
        sync_input = (args.sync_frame, args.sync_timestamp)
    if args.frame_extract_start and args.frame_extract_end:
        frames = (args.frame_extract_start[0], args.frame_extract_end[0])
    """Remove?
    if args.label and args.gif:
        label_and_gif = (args.label, args.gif)
    elif args.label:
        label_and_gif = (args.label, False)
    elif args.gif:
        label_and_gif = (False, args.gif)
    else:
        label_and_gif = (True, False)
    """
    lb = gif = bbox = False 
    if args.label:
        lb = True
    if args.gif:
        gif = True
    if args.bbox:
        bbox = True
    lb_gif_bbox = (lb, gif, bbox)


    # process args
    args_static_obj_gpx_video(generic_so_file = args.static_object_file,
                              gpx_file = args.gpx_file,
                              video_file = args.video_file,
                              vid_sync = sync_input, 
                              frame_extract = frames, 
                              extra_out = lb_gif_bbox
                              )


if __name__ == "__main__":
    main()