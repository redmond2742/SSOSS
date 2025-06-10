# !/usr/bin/env python
# coding: utf-8
import glob
import os
import shutil
import subprocess
from pathlib import PurePath, Path
from datetime import timedelta, timezone, datetime
import dateutil
import numpy as np
from tqdm import tqdm
import cv2
import imageio
from PIL import Image
import piexif


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
        self.image_out_path = self.video_dir / "out"
        self.image_out_path.mkdir(exist_ok=True, parents=True)

        self.fps = self.get_fps()
        self.frame_count = self.get_frame_count()
        self.duration = self.get_duration()
        self.start_time = 0
        self.capture = ""


        self.vid_summary(vid_summary=True)

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
        """
        finds start time of video based on frame and timestamp
            appends frame # and timestamp to sync.txt with video filename for reference
        """
        sync_txt_folder = Path(self.video_dir, "out")
        sync_file = str(sync_txt_folder) +"/"+ "sync.txt"
        with open(sync_file, 'a') as f:
            f.write(f'{self.video_filepath.stem},{frame},{ts}\n')

        elapsed_time = frame / self.fps
        if type(ts) is float:
            start_time = ts - elapsed_time
        else:
            t_temp = (dateutil.parser.isoparse(ts))  #  isoparse parses ISO-8601 datetime string into datetime.datetime
            start_time = t_temp.replace(tzinfo=timezone.utc).timestamp() - elapsed_time
        self.set_start_utc(start_time)
        self.vid_summary(vid_summary=False, sync=True)
        return None

    def create_pic_list_from_zip(self, i_desc_timestamps):
        """returns sight distance description text and frame of video to extract as 2 lists"""
        intersection_desc = []
        frames = []
        prev_frame = 0
        filename_description, time_of_sd = zip(*i_desc_timestamps)

        for sd_item in range(0, len(i_desc_timestamps)):
            time_of_picture = time_of_sd[sd_item] - self.get_start_timestamp()
            if time_of_picture > 0 and time_of_picture <= self.get_duration():
                frame_of_video = time_of_picture * self.fps

                #  build up lists if not duplicate frame
                if int(frame_of_video) > int(prev_frame):
                    intersection_desc.append(filename_description[sd_item])
                    frames.append(int(frame_of_video))
                prev_frame = frame_of_video

        return intersection_desc, frames

    def save_frame_ffmpeg(self, frame_number: int, output_path: Path) -> None:
        """Save a specific frame quickly using ffmpeg."""
        timestamp = frame_number / self.fps
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(timestamp),
            "-i",
            str(self.video_filepath),
            "-frames:v",
            "1",
            str(output_path),
        ]
        subprocess.run(cmd, check=True)

    @staticmethod
    def _deg_to_dms_rational(value: float):
        """Helper to convert decimal degrees to EXIF rational format."""
        abs_value = abs(value)
        deg = int(abs_value)
        min_float = (abs_value - deg) * 60
        minute = int(min_float)
        sec = round((min_float - minute) * 60 * 1000000)
        return ((deg, 1), (minute, 1), (sec, 1000000))

    @staticmethod
    def write_gps_exif(image_path: Path, latitude: float, longitude: float) -> None:
        """Write GPS latitude and longitude EXIF tags to ``image_path``."""
        img = Image.open(image_path)
        lat_ref = "N" if latitude >= 0 else "S"
        lon_ref = "E" if longitude >= 0 else "W"
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLatitude: ProcessVideo._deg_to_dms_rational(latitude),
            piexif.GPSIFD.GPSLongitudeRef: lon_ref,
            piexif.GPSIFD.GPSLongitude: ProcessVideo._deg_to_dms_rational(longitude),
        }

        try:
            exif_dict = piexif.load(img.info.get("exif", b""))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict.setdefault("GPS", {}).update(gps_ifd)
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))
        img.close()
    
    def extract_generic_so_sightings(self, desc_timestamps, project, label_img=True, gen_gif=False):
        """
        extract generic sighting images from video based on description and timestamp zip

        desc_timestamps: sorted list of tuples (filename description, timestamp of sight distance)
        project: instance of ProcessRoadObjects() class
        """

        generic_so_desc, extract_frames = self.create_pic_list_from_zip(desc_timestamps)
        image_path = Path(self.video_dir, "out", self.video_filepath.stem, "generic_static_object_sightings/")
        image_path.mkdir(exist_ok=True, parents=True)

        for desc, frame_num in tqdm(
                list(zip(generic_so_desc, extract_frames)),
                desc="Frame Extraction",
                unit=" frame"):
            frame_name = str(desc) + '.jpg'
            frame_filepath = image_path / frame_name
            self.save_frame_ffmpeg(frame_num, frame_filepath)
            ts = float(desc.split('-')[-1])
            location = project.get_location_at_timestamp(ts)
            if location is not None:
                self.write_gps_exif(frame_filepath, location.latitude, location.longitude)
            print(
                f'PICTURE CAPTURED AT {frame_num}: {desc}, Saved {generic_so_desc.index(desc) + 1} picture(s) of {len(extract_frames)}')

        if label_img:
            self.generic_so_img_overlay_info_box(self.video_filename, project)
        if gen_gif:
            self.generate_gif(desc_timestamps, project)

    def extract_sightings(self, desc_timestamps, project, label_img=True, gen_gif=False):
        """
        extract sighting images from video based on description and timestamp zip

        desc_timestamps: sorted list of tuples (filename description, timestamp of sight distance)
        project: instance of ProcessRoadObjects() class
        """

        intersection_desc, extract_frames = self.create_pic_list_from_zip(desc_timestamps)
        image_path = Path(self.video_dir, "out", self.video_filepath.stem, "signal_sightings/")
        image_path.mkdir(exist_ok=True, parents=True)

        for desc, frame_num in tqdm(
                list(zip(intersection_desc, extract_frames)),
                desc="Frame Extraction",
                unit=" frame"):
            frame_name = str(desc) + '.jpg'
            frame_filepath = image_path / frame_name
            self.save_frame_ffmpeg(frame_num, frame_filepath)
            ts = float(desc.split('-')[-1])
            location = project.get_location_at_timestamp(ts)
            if location is not None:
                self.write_gps_exif(frame_filepath, location.latitude, location.longitude)
            print(
                f'PICTURE CAPTURED AT {frame_num}: {desc}, Saved {intersection_desc.index(desc) + 1} picture(s) of {len(extract_frames)}')

        if label_img:
            self.img_overlay_info_box(self.video_filename, project)
        if gen_gif:
            self.generate_gif(desc_timestamps, project)
        """
        if bbox:
        self.img_overlay_bbox(description_list,project)
    
        """    
     

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

        start_frame = int(self.get_fps() * start_sec)
        end_frame = int(self.get_fps() * end_sec)

        for i in range(start_frame, end_frame + 1):
            frame_name = 'Frame' + str(i) + '.jpg'
            frame_filepath = image_path / frame_name
            self.save_frame_ffmpeg(i, frame_filepath)
            print(f'Saved Image {i} to {frame_filepath}')

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

            for j in range(frame_min, frame_max + 1):
                frame_name = str(j) + "-" + intersection_desc[i] + '.jpg'
                frame_filepath = gif_path / frame_name
                self.save_frame_ffmpeg(j, frame_filepath)
            i += 1
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

    def vid_summary(self, vid_summary, sync=False):
        #  display values
        width = 70
        title = "VIDEO SUMMARY"
        symbol = "="
        sync_title = "VIDEO SYNCHRONIZATION SUMMARY"

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
                # Total Number of Frames: {self.frame_count:,}
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
        if vid_summary:
            print(summary)
        if sync:
            print(sync_time)


    @staticmethod
    def find_font_scale(label, max_width = 0, max_height = 0):
        font_scl = 0.2
        textsize_x, textsize_y = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, font_scl, 1)[0]
        w_font_scl = h_font_scl = font_scl
        if max_width > 0:
            if textsize_x < max_width:
                #  scale up scale in for loop
                for scale_increment in np.arange(0, 10, 0.1):
                    w_font_scl = scale_increment
                    textsize_x, textsize_y = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, w_font_scl, 1)[0]
                    if textsize_x < max_width:
                        continue
                    else:
                        w_font_scl = scale_increment - 0.5
                        break
        if max_height > 0:
            if textsize_y < max_height:
                #  scale up scale in for loop
                for scale_increment in np.arange(0, 10, 0.1):
                    h_font_scl = scale_increment
                    textsize_x, textsize_y = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, h_font_scl, 1)[0]
                    if textsize_y < max_height:
                        continue
                    else:
                        h_font_scl = scale_increment - 0.5
                        break
        if max_width > 0  and max_height > 0:
            return min(w_font_scl, h_font_scl)
        else:
            return max(w_font_scl, h_font_scl)

    @staticmethod
    def find_x_start_new_label(x_size, w, label):
        start_x = 0
        trunc_label = label[:]
        if x_size <= w:
            start_x = int((w - x_size) / 2.0)
        else:
            start_x = 0
            trunc_label = label[0:w]
        return start_x, trunc_label

            
    def labels(self, img, output_filename, descriptive_label, height_percent:tuple, ssoss_and_descriptive = True ):

        alpha = 1  # Transparency factor.
        text_font = cv2.FONT_HERSHEY_PLAIN
        font_thickness = 1
        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)
        img_copy = img.copy()

        # given inputs
        img_height, img_width, channels = img.shape
        descriptive_label_percent, ssoss_percent = height_percent

        # calculated descriptive label dimensions
        descriptive_label_height = int(img_height * descriptive_label_percent)
        descriptive_label_y = img_height - descriptive_label_height
        font_scale = self.find_font_scale(descriptive_label, max_width = img_width)
        textsize_x, textsize_y = cv2.getTextSize(descriptive_label, text_font,  font_scale, font_thickness)[0]
        text_y = int((img_height - descriptive_label_height/2.0)+textsize_y/2.0)
        text_x, descriptive_label = self.find_x_start_new_label(textsize_x, img_width, descriptive_label)

        if ssoss_and_descriptive:

            ssoss_label = "Created using Free and Open Source Software: Safe Sightings of Signs and Signals (SSOSS): Github.com/redmond2742/ssoss"

            # calculated ssoss_ad dimensions
            ssoss_label_height = int(img_height * ssoss_percent)
            ssoss_label_font_scale = self.find_font_scale(ssoss_label, max_height = ssoss_label_height)
            ssoss_label_textsize_x, ssoss_textsize_y = cv2.getTextSize(ssoss_label, text_font, ssoss_label_font_scale, 1)[0]
            
            ssoss_label_text_x = int((img_width - ssoss_label_textsize_x) / 2.0)
            ssoss_label_text_y = int(img_height)

            ssoss_text_x, fitted_ssoss_label = self.find_x_start_new_label(ssoss_label_textsize_x, img_width, ssoss_label)

            # Calculated y-coordinates for different labels
            ssoss_label_y = img_height - ssoss_label_height  # y-coordinate of top of ssoss ad
            above_descriptive_and_ssoss_label_y = ssoss_label_y - descriptive_label_height # y-coordinate of top of descriptive label
            descriptive_and_ssoss_label_text_y = ssoss_label_y - int(textsize_y/2.0)

            #ssoss ad box
            cv2.rectangle(img_copy,pt1=(0, img_height), pt2=(img_width, ssoss_label_y), color = BLACK, thickness=-1)
            ssoss_and_descriptive_label = cv2.addWeighted(img_copy, alpha, img, 1-alpha, 0)
            #image label box
            cv2.rectangle(img_copy, pt1=(0, ssoss_label_y), pt2=(img_width, above_descriptive_and_ssoss_label_y), color=WHITE, thickness=-1)
            ssoss_and_descriptive_label = cv2.addWeighted(img_copy, alpha, img, 1-alpha, 0)
            # text for ssoss ad and label
            ssoss_and_descriptive_label = cv2.putText(ssoss_and_descriptive_label, descriptive_label, (text_x, descriptive_and_ssoss_label_text_y), text_font, font_scale, BLACK, 2)
            ssoss_and_descriptive_label = cv2.putText(ssoss_and_descriptive_label, fitted_ssoss_label, (ssoss_text_x, ssoss_label_text_y), text_font, ssoss_label_font_scale, WHITE, 2)
            # save image
            cv2.imwrite(output_filename, ssoss_and_descriptive_label)
        
        else:
            # no ssoss label, just descriptive label (not recommended)
            cv2.rectangle(img_copy, pt1=(0, img_height), pt2=(img_width, descriptive_label_y), color=WHITE, thickness=-1)
            img_new = cv2.addWeighted(img_copy, alpha, img, 1-alpha, 0)
            cv2.putText(img_new, descriptive_label, (text_x, text_y), text_font, font_scale, BLACK, 2)
            cv2.imwrite(output_filename, img_new)

    @staticmethod
    def generate_descriptive_label(path, fn, road_object_info, static_object_type="generic"):
        sro_id = int(fn.split(".")[0])
        ts = float(fn.split("-")[-1].replace(".jpg", ""))
        distance = 0
        if static_object_type == "intersection":
            b_index = int((fn.rsplit(".")[1])[0:1])
            descriptive_label = road_object_info.intersection_frame_description(sro_id, b_index, distance, ts, desc_type="label")
        else:
            descriptive_label = road_object_info.generic_so_description(sro_id, distance, ts, desc_type="label")
        return descriptive_label
    
    def generic_so_img_overlay_info_box(self, vid_filename_dir, ro_info):
        img_path = Path(self.video_dir, "out", self.video_filepath.stem, "generic_static_object_sightings/")
        label_img_path = Path(img_path, "labeled/")
        os.makedirs(label_img_path, exist_ok=True)

        img_dir_string = str(img_path)
        label_img_dir_string = str(label_img_path)
        pattern_criteria = ['*.jpg','[!.]*']

        descriptive_label_percent = 0.05 # 5% for descriptive label at bottom of image
        ssoss_label_percent = 0.02 #  2% for ssoss advertisement label at very bottom of image
        label_height_percents = (descriptive_label_percent, ssoss_label_percent)

        #  filter for images where * is wildcard and don't include hidden (.*) files
        pathlist = [f for f in Path(img_dir_string).rglob('*.jpg') if not str(f).startswith(".")]
        for file in pathlist:
            if not str(file.stem).startswith("."):
                filename = str(Path(file).name)
                img_path = img_dir_string + "/" + filename
                img = cv2.imread(img_path)
                overlay = img.copy()

                label_img_name = str(Path(label_img_path, filename))
                descriptive_label = self.generate_descriptive_label(label_img_path, filename, ro_info)

                self.labels(img, label_img_name, descriptive_label, label_height_percents)
           

    def img_overlay_info_box(self, vid_filename_dir, ro_info):
        img_path = Path(self.video_dir, "out", self.video_filepath.stem, "signal_sightings/")
        label_img_path = Path(img_path, "labeled/")
        os.makedirs(label_img_path, exist_ok=True)

        img_dir_string = str(img_path)
        label_img_dir_string = str(label_img_path)
        pattern_criteria = ['*.[0-3]-*.jpg','[!.]*']

        descriptive_label_percent = 0.05 # 5% for descriptive label at bottom of image
        ssoss_label_percent = 0.02 #  2% for ssoss advertisement label at very bottom of image
        label_height_percents = (descriptive_label_percent, ssoss_label_percent)

        #  filter for images where * is wildcard and don't include hidden (.*) files
        pathlist = [f for f in Path(img_dir_string).rglob('*.[0-3]-*.jpg') if not str(f).startswith(".")]
        for file in pathlist:
            if not str(file.stem).startswith("."):
                filename = str(Path(file).name)
                img_path = img_dir_string + "/" + filename
                img = cv2.imread(img_path)
                overlay = img.copy()

                label_img_name = str(Path(label_img_path, filename))
                descriptive_label = self.generate_descriptive_label(label_img_path, filename,ro_info, static_object_type="intersection")

                self.labels(img, label_img_name, descriptive_label, label_height_percents)
