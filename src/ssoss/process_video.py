# !/usr/bin/env python
# coding: utf-8
import glob
import os
import shutil
from pathlib import PurePath, Path
from datetime import timedelta, timezone, datetime
import dateutil
import numpy as np
from tqdm import tqdm
import cv2
import imageio


class ProcessVideo:

    def __init__(self, video_filestring: str):
        """Process video files using methods to extract range of frames,
        extract frame at precise UTC time, or generate gif from selection of images.
        Note: For syncing video and GPX, use sync() method.

        :param in_dir_path: filename of video to be processed (include video extension (.mov, .mp4, etc)
        """

        self.DATE_FORMAT = '%m-%d-%Y--%H-%M-%S.%f-%Z'  #ISO 8601 format
        self.video_dir = Path(video_filestring).parents[0]
        self.video_filepath = Path(video_filestring)
        self.video_filename = Path(video_filestring).name
        self.image_out_path = self.video_dir / "out/"
        self.image_out_path.parent.mkdir(exist_ok=True, parents=True)

        self.fps = self.get_fps()
        self.frame_count = self.get_frame_count()
        self.duration = self.get_duration()
        self.start_time = 0
        self.capture = ""

        self.vid_summary()

    def set_start_utc(self, video_start_time):
        self.start_time = video_start_time
        return None

    def get_start_timestamp(self):
        return self.start_time

    def get_fps(self):
        self.capture = cv2.VideoCapture(str(self.video_filepath))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.capture.release()
        return self.fps

    def get_frame_count(self):
        self.capture = cv2.VideoCapture(str(self.video_filepath))
        self.frame_count = self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
        self.capture.release()
        return self.frame_count

    def get_duration(self, seconds_output=True):
        self.duration = self.frame_count / self.fps
        if seconds_output:
            return self.duration
        else:
            return timedelta(seconds=self.duration)

    def sync(self, frame: int, ts):
        elapsed_time = frame / self.fps
        if type(ts) is float:
            start_time = ts - elapsed_time
        else:
            t_temp = (dateutil.parser.isoparse(ts))  #  isoparse parses ISO-8601 datetime string into datetime.datetime
            start_time = t_temp.replace(tzinfo=timezone.utc).timestamp() - elapsed_time
        self.set_start_utc(start_time)
        self.vid_summary(sync=True)
        return None

    def create_pic_list_from_zip(self, i_desc_timestamps):
        """returns sight distance description text and frame of video to extract as 2 lists"""
        intersection_desc = []
        frames = []
        prev_frame = 0
        filename_description, time_of_sd = zip(*i_desc_timestamps)

        for sd_item in range(0, len(i_desc_timestamps)):
            time_of_picture = time_of_sd[sd_item] - self.get_start_timestamp()
            if time_of_picture > 0:
                frame_of_video = time_of_picture * self.fps

                #  build up lists if not duplicate frame
                if int(frame_of_video) > int(prev_frame):
                    intersection_desc.append(filename_description[sd_item])
                    frames.append(int(frame_of_video))
                prev_frame = frame_of_video

        return intersection_desc, frames

    def extract_sightings(self, desc_timestamps, project, gen_gif=False):
        """
        extract sighting images from video based on description and timestamp zip

        desc_timestamps: sorted list of tuples (filename description, timestamp of sight distance)
        project: instance of ProcessRoadObjects() class
        """

        intersection_desc, extract_frames = self.create_pic_list_from_zip(desc_timestamps)
        image_path = Path(self.video_dir, "out", self.video_filepath.stem, "sightings/")
        image_path.mkdir(exist_ok=True, parents=True)

        #image_path = str(self.image_out_path) + "/" + self.video_filename + "/"
        #os.makedirs(image_path, exist_ok=True)

        capture = cv2.VideoCapture(str(self.video_filepath))
        frame_count = self.get_frame_count()

        i = 0  # index for all frames to extract
        j = 0  # index for frames list to extract as image
        k = 0  # intersection string description counter

        while capture.isOpened() and len(extract_frames) > 0 and i < frame_count:

            for current_frame in tqdm(range(0, extract_frames[-1]),
                          desc="Frame Search",
                          unit=" Frames"):
                ret, frame = capture.read()
                if ret is False:
                    print("ERROR: ret is FALSE on OpenCV image")
                    break
                if i == extract_frames[j] and j <= len(extract_frames)-1:
                    frame_name = str(intersection_desc[j]) + '.jpg'
                    frame_filepath = image_path / frame_name
                    cv2.imwrite(str(frame_filepath), frame)
                    print(
                        f'PICTURE CAPTURED AT {extract_frames[j]}: {intersection_desc[j]}, Saved {j + 1} picture(s) of {len(extract_frames)}')
                    j += 1
                    k += 1
                if j == len(extract_frames):
                    print("done processing images")
                    capture.release()
                    break
                i += 1
            if i > extract_frames[-1]:
                break
        capture.release()

        self.img_overlay_info_box(self.video_filename, project)
        if gen_gif:
            self.generate_gif(desc_timestamps, project)

    #  TODO: convert to start_sec, start_min=0, end_sec, end_min=0, folder="")
    def extract_frames_between(self, start_sec, end_sec):
        """ helper function to extract frames from video during a specific time period to estimate offset
            between gpx and video

        :param start_sec: start time of video to extract image frames
        :param end_sec: end time of video to extract image frames
        """
        """ 

            ===need to know====
            time of start of gpx:
            frame # of video at a logged location on GPX file
            time of frame at location in GPX file

            Calculate:
            Big_Offset: time of frame at location in GPX file - Start of GPX file


            ============

            When is video actually available during GPX trax recording?


            seconds of video  = frame of video / fps

            Adj_Offset = time of frame at location in GPX file - seconds of video

            if adj_off < (time of frame at location in GPX file- Start time of GPX file):
                Clip GPX to shorter file that matches video.

            def video_start_utc():
                this uses gpx file and frame of gpx point to calculate when video started=

            """
        image_path = Path(self.video_dir, "out", self.video_filepath.stem, "frames/")
        image_path.mkdir(exist_ok=True, parents=True)

        capture = cv2.VideoCapture(str(self.video_filepath))
        #print(f'Video is Open: {self.capture.isOpened()}')
        i = 0
        start_frame = int(self.get_fps() * start_sec)
        end_frame = int(self.get_fps() * end_sec)

        while capture.isOpened():
            ret, frame = capture.read()
            if ret == False:
                break
            if start_frame <= i and i <= end_frame:
                frame_name = 'Frame' + str(i) + '.jpg'
                frame_filepath = image_path / frame_name
                cv2.imwrite(str(frame_filepath), frame)
                print(f'Saved Image {i} to {frame_filepath}')
            i += 1

            if i > end_frame:
                capture.release()
                break
        capture.release()

    def generate_gif(self, desc_timestamps, project, distance=100):
        """ creates a folder of images to create a gif
        # /////////////*\\\\\\\\\\\\\\\
        # For a given sight distance timestamp location "*" calculate frames needed for gif,
        # before "/" and after"\" frames from a point of interest "*"

        # methodology
        # 1. find what frames to extract
        # 2. extract frames into folder for .gif
        # 3. create gif from those frames
        # 4. delete folder of frames and just keep .gif

        :param df: dataframe of key points including speed, and descriptions of the point
        :param frame_list: list of key frame at a distance to check sight of static object
        :param distance: distance (units=feet) before AND after of key frame to make images for
        :return: Returns a .gif filetype
        """

        intersection_desc, frame_list = self.create_pic_list_from_zip(desc_timestamps)

        for i in tqdm(range(0, len(desc_timestamps)),
                      desc="Generating Images for GIF",
                      unit=" Location"):
            gif_basepath = self.video_dir / "out" / self.video_filepath.stem / "gif" / intersection_desc[i]
            gif_path = Path(gif_basepath)
            gif_path.mkdir(exist_ok=True, parents=True)

            # crude approx of avg speed between two points.
            speed = project.get_speed_at_timestamp(desc_timestamps[i][1])
            if speed is not None and speed > 0.0:
                additional_frames = int((distance / speed) * self.fps) + 1
            else:
                additional_frames = 0

            frame_min = 0
            frame_max = self.frame_count

            if (frame_list[i] - additional_frames) <= 0:
                frame_min = 0
            else:
                frame_min = int(frame_list[i] - additional_frames)

            if (frame_list[i] + additional_frames) >= self.frame_count:
                frame_max = int(self.frame_count)
            else:
                frame_max = int(frame_list[i] + additional_frames)

            j = 0  # frame index
            capture = cv2.VideoCapture(str(self.video_filepath))
            while capture.isOpened():
                ret, frame = capture.read()
                if ret is False:
                    break
                if frame_min <= j <= frame_max:
                    frame_name = str(j) + "-" + intersection_desc[i] + '.jpg'
                    frame_filepath = gif_path / frame_name
                    cv2.imwrite(str(frame_filepath), frame)
                if j > frame_max:
                    break
                else:
                    j += 1
            i += 1
        capture.release()
        self.assemble_gif()

    def assemble_gif(self):
        #base_path = Path(self.video_dir, "out", self.video_filepath.stem, "gif/")
        gif_files_path = self.video_dir / "out" / self.video_filepath.stem / "gif"
        base_path = Path(gif_files_path)
        #base_path = "./out/frames/" + self.video_filename + "/gif/"
        img_folders = sorted(base_path.glob('*'))
        kargs = {'duration': 1/9999999999999999}
        for i in range(0, len(img_folders)):
            images = []
            img_folder = os.path.basename(img_folders[i])
            frame_images = sorted(glob.glob(os.path.join(base_path, img_folder + "/*.jpg")))
            for j in range(0, len(frame_images)):
                if j % 5 == 0:
                    images.append(imageio.imread(frame_images[j]))
            imageio.mimsave(os.path.join(base_path, img_folder + ".gif"), images, **kargs)
            print(f'Created Gif: {img_folder}.gif')
            #  TODO: delete folder of images after gif is created.
            #  TODO: overwite existing gif option



    @staticmethod
    def hr_min_sec(sec):
        if sec < 60:
            return f'{sec} seconds'
        elif sec < 3600:
            minutes = int(sec / 60)
            sec_remain = round(sec - minutes * 60, 2)
            return f'{minutes:02}:{sec_remain:05.2f} (MM:SS.ss)'
        elif sec >= 3600:
            hr = int(sec / 3600)
            minutes = int(sec / 60)
            sec_remain = round(sec - minutes * 60, 2)
            return f'{hr:02}:{minutes:02}:{sec_remain:05.2f} (HH:MM:SS.ss)'

    def sizeConvert(self, size):
        # convert filesize to human readable format
        K, M, G = 1024, 1024 ** 2, 1024 ** 3
        if size >= G:
            return str(round(size / G, 2)) + ' GB'
        elif size >= M:
            return str(round(size / M, 2)) + ' MB'
        elif size >= K:
            return str(round(size / K, 2)) + ' KB'
        else:
            return str(round(size, 2)) + ' Bytes'

    def get_filesize(self):
        # get the file size
        file_byte = os.path.getsize(self.video_filepath)
        return self.sizeConvert(file_byte)

    def vid_summary(self, sync=False):
        #  display values
        width = 70
        title = "VIDEO SUMMARY"
        symbol = "="
        sync_title = "Sync Start Time"

        vid_file = cv2.VideoCapture(str(self.video_filepath))
        if vid_file.isOpened():
            # get vcap property
            vid_width = vid_file.get(cv2.CAP_PROP_FRAME_WIDTH)  # float `width`
            vid_height = vid_file.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`

        summary = f"""
                {symbol * width}
                {" " * (int(width/2)-int(len(title)/2))}{title}
                {symbol * width}
                # Video File: {str(self.video_filepath)}
                # Video File Size: {self.get_filesize()}
                # Resolution (w x h): {vid_width} x {vid_height} ({round((vid_width * vid_height)/(1*10**6),1)}MP)
                # Frames Per Second: {self.fps}
                # Total Number of Frames: {self.frame_count}
                # Total Duration: {self.hr_min_sec(self.get_duration())}
                {symbol * width}
                """

        sync_time = f"""
                    {symbol * width}
                    {" " * (int(width/2)-int(len(sync_title)/2))}{sync_title}
                    {symbol * width}
                    # Start Time: {datetime.fromtimestamp(self.start_time, tz=None)}
                    # End Time:   {datetime.fromtimestamp(self.start_time + self.get_duration(), tz=None)}
                    {symbol * width}
                    """

        if not sync:
            print(summary)
        else:
            print(sync)


    @staticmethod
    def find_font_scale(label, max_width):
        font_scl = 0.1
        textsize_x, textsize_y = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, font_scl, 1)[0]
        if textsize_x < max_width:
            #  scale up scale in for loop
            for scale_increment in np.arange(0, 10, 0.1):
                font_scl = scale_increment
                textsize_x, textsize_y = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, font_scl, 1)[0]
                if textsize_x < max_width:
                    continue
                else:
                    font_scl = scale_increment - 0.1
                    break
        return font_scl

    def img_overlay_info_box(self, vid_filename_dir, ro_info):
        img_path = Path(self.video_dir, "out", self.video_filepath.stem, "sightings/")
        label_img_path = Path(img_path, "labeled/")
        os.makedirs(label_img_path, exist_ok=True)

        alpha = 1  # Transparency factor.
        text_font = cv2.FONT_HERSHEY_PLAIN
        font_thickness = 1

        img_dir_string = str(img_path)
        label_img_dir_string = str(label_img_path)

        pathlist = Path(img_dir_string).rglob('*.[0-3]-*.jpg') #  filter for images where * is wildcard
        for file in pathlist:
            filename = str(Path(file).name)
            img_path = img_dir_string + "/" + filename
            img = cv2.imread(img_path)
            overlay = img.copy()

            label_img_name = str(Path(label_img_path, filename))

            # get img dimensions
            img_height, img_width, channels = img.shape
            rect_h = int(img_height * 0.05)
            rect_w = img_width
            rect_y = img_height-rect_h

            # build label
            sro_id = int(filename.split(".")[0])
            b_index = int((filename.rsplit(".")[1])[0:1])
            distance = 0
            ts = float(filename.split("-")[-1].replace(".jpg", ""))
            label = ro_info.intersection_frame_description(sro_id, b_index, distance, ts, desc_type="label")
            font_scale = self.find_font_scale(label, rect_w)
            textsize_x, textsize_y = cv2.getTextSize(label, text_font,  font_scale, font_thickness)[0]
            text_y = int((img_height - rect_h/2.0)+textsize_y/2.0)

            if textsize_x <= rect_w:
                text_x = int((rect_w-textsize_x)/2.0)
            else:
                text_x = 0
                label = label[0:rect_w]

            # (x,y))
            """
            0,0                                                              img_width,0
            
            
            
            0, img_height - img_height*5%             img_width, img_height - img_height*5%
            
            0,img_height                                             img_width, img_height
            """
            cv2.rectangle(overlay, pt1=(0, img_height), pt2=(rect_w, rect_y), color=(255, 255, 255), thickness=-1)
            img_new = cv2.addWeighted(overlay, alpha, img, 1-alpha, 0)
            cv2.putText(img_new, label, (text_x, text_y), text_font, font_scale, (0, 0, 0), 2)
            cv2.imwrite(label_img_name, img_new)
