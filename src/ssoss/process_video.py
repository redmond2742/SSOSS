# !/usr/bin/env python
# coding: utf-8
import os
from pathlib import PurePath, Path

import dateutil
import numpy as np

from tqdm import tqdm
from datetime import timedelta, timezone, datetime

import cv2


class ProcessVideo:

    def __init__(self, video_filename, in_dir_path=PurePath("./in/"), in_video_dir_path=PurePath("gpx_video/")):
        """Process video files using methods to extract range of frames,
        extract frame at precise UTC time, or generate gif from selection of images.
        Note: For syncing video and GPX, use set_start_utc()

        :param in_dir_path: filename of video to be processed (include video extension (.mov, .mp4, etc)
        """

        self.DATE_FORMAT = '%m-%d-%Y--%H-%M-%S.%f-%Z'  #ISO 8601 format
        self.video_filepath = in_dir_path / in_video_dir_path / video_filename  # video path and filename
        self.video_filename = video_filename
        self.image_out_path = PurePath("./out/frames/")
        self.fps = self.get_fps()
        self.frame_count = self.get_frame_count()
        self.duration = self.get_duration()
        self.start_time = 0
        self.capture = ""


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
            t_temp = (dateutil.parser.isoparse(ts))
            start_time = t_temp.replace(tzinfo=timezone.utc).timestamp() - elapsed_time
        self.set_start_utc(start_time)
        self.vid_summary()
        return None

    def create_pic_list_from_zip(self, i_desc_timestamps):
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

    def extract_images(self, desc_timestamps):
        """ extract images from video based on description and timestamp zip"""
        intersection_desc, extract_frames = self.create_pic_list_from_zip(desc_timestamps)
        image_path = str(self.image_out_path) + "/" + self.video_filename + "/"
        os.makedirs(image_path, exist_ok=True)

        capture = cv2.VideoCapture(str(self.video_filepath))
        frame_count = self.get_frame_count()

        i = 0  # index for all frames to extract
        j = 0  # index for frames list to extract as image
        k = 0  # intersection string description counter

        while capture.isOpened() and len(extract_frames) > 0 and i < frame_count:

            for current_frame in tqdm(range(0, extract_frames[-1]), #tqdm(range(0, extract_frames[-1]),
                          desc="Frame Search",
                          unit=" Frames"):
                ret, frame = capture.read()
                if ret is False:
                    print("ERROR: ret is FALSE on OpenCV image")
                    break
                if i == extract_frames[j] and j <= len(extract_frames)-1:
                    cv2.imwrite(
                        image_path + str(intersection_desc[j]) + '.jpg', frame)
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

    #  TODO: convert to start_sec, start_min=0, end_sec, end_min=0, folder="")
    def extract_frames_between(self, start_sec, end_sec, folder=""):
        """ helper function to extract frames from video during a specific time period to estimate offset
            between gpx and video

        :param start_sec:
        :param end_sec:
        :param folder:
        :return:
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
        # TODO: consider another subfolder for this video filename
        image_path = './out/frames/' + self.video_filename + "/" + folder + "/"
        os.makedirs(image_path, exist_ok=True)

        print(str(self.video_filepath))

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
                cv2.imwrite(image_path + 'Frame' + str(i) + '.jpg', frame)
                print(f'Saved Image Frame {i} to {image_path}')
            i += 1

            if i > end_frame:
                capture.release()
                break
        capture.release()
        """
            sd_frame_num = int(time_delay * self.fps)
    
            print(f'sd_frame: {sd_frame_num}')
    
            for j in range(0, sd_frame_num)+10:
    
                ret, frame = self.video.read()
                if ret == True:
                    print(j)
                    if j == sd_frame_num:
                        cv2.imwrite("filename%d.jpg" % j, frame)
    
    
            #self.video.release()
            """

    def generate_gif_images(self, df, frame_list: list, distance):
        """ creates a folder of images to create a gif
        # /////////////*\\\\\\\\\\\\\\\
        # calculate frames needed for gif, before "/" and after frame "\" from sight Distance "*" location

        # Algo methodology
        # 1. find what frames to extract
        # 2. extract frames into folder for gif
        # 3. create gif from those frames

        :param df: dataframe of key points including speed, and descriptions of the point
        :param frame_list: list of key frame at a distance to check sight of static object
        :param distance: distance in feet before AND after of key frame to make images for
        :return: Returns a .gif filetype
        """

        # TODO: convert speed from meters/sec to feet per second
        capture = cv2.VideoCapture(self.video_filepath)
        print(f'Video is Open: {self.capture.isOpened()}')

        for i in range(0, len(frame_list)):

            folder = df.string_desc.loc[i]
            image_path = './out/frames/gif/' + folder + "/"
            os.makedirs(image_path, exist_ok=True)

            # assumes constant speed from this center point
            additional_frames = int((distance / df.spd.loc[i]) * self.fps) + 1

            print(
                f'center frame: {frame_list[i]}, additional_frame:{additional_frames}'
            )

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

            print(
                f'min frame: {frame_min}, max frame:{frame_max}/{frame_list[i]}'
            )
            # i is df index
            j = 0  # frame index

            capture = cv2.VideoCapture(self.video_file)
            print(f'Video is Open: {self.capture.isOpened()}')

            while capture.isOpened():
                ret, frame = capture.read()
                if ret is False:
                    break
                print(f'intersection #:{i}, frame #:{j}')
                if frame_min <= j <= frame_max:
                    cv2.imwrite(
                        image_path + str(j) + ":" + df.string_desc.loc[i] +
                        '.jpg', frame)
                    print(
                        f'PICTURE CAPTURED AT FRAME:{j}: {df.string_desc.loc[i]}'
                    )
                if j > frame_max:
                    break
                else:
                    j += 1
            i += 1
        capture.release()



    @staticmethod
    def hr_min_sec(sec):
        if sec < 60:
            return f'{sec} seconds'
        elif sec < 3600:
            min = int(sec / 60)
            sec_remain = round(sec - min * 60, 2)
            return f'{min}:{sec_remain} (MM:SS.ss)'
        elif sec >= 3600:
            hr = int(sec / 3600)
            min = int(sec / 60)
            sec_remain = round(sec - min * 60, 2)
            return f'{hr}:{min}:{sec_remain} (HH:MM:SS.ss)'

    def sizeConvert(self, size):
        # size convert
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

    def vid_summary(self):
        #  display values
        width = 70
        title = "VIDEO SUMMARY"
        symbol = "="

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
                # Start Time: {datetime.fromtimestamp(self.start_time, tz=None)}
                # End Time:   {datetime.fromtimestamp(self.start_time + self.get_duration(), tz=None)}
                {symbol * width}
                """

        print(summary)

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
        dir_as_string = str(self.image_out_path) + "/" + vid_filename_dir
        alpha = 1  # Transparency factor.
        text_font = cv2.FONT_HERSHEY_PLAIN
        font_thickness = 1

        pathlist = Path(dir_as_string).rglob('*.[0-3]-*.jpg') #  filter for images where * is wildcard
        for file in pathlist:
            filename = str(file).split("/")[-1]
            img_path = dir_as_string + "/" + filename
            img = cv2.imread(img_path)
            overlay = img.copy()

            label_img_dir = dir_as_string + "/labeled/"
            os.makedirs(label_img_dir, exist_ok=True)
            label_img_name = label_img_dir + filename

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
