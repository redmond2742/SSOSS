# !/usr/bin/env python
# coding: utf-8

import csv
import os
from datetime import datetime, timezone
from pathlib import Path, PurePath

import geopy
import gpxpy
import gpxpy.gpx

import pandas as pd
from geopy.distance import geodesic, Distance
import lxml
from lxml import etree
from tqdm import tqdm

from ssoss.static_road_object import Intersection
from ssoss.motion_road_object import GPXPoint


class ProcessRoadObjects:

    def __init__(self,
                 signals_filename: str,
                 gpx_filename: str,
                 in_dir_path=PurePath("./in/"),
                 in_gpx_dir_path=PurePath("gpx_video/"),
                 out_dir_path=PurePath("./out/")
                 ):
        """ Class to process Road Object files. Using January 1st 1970 as time epoc

        :in_dir_path - defaults to ./in/
        :in_gpx_dir_path = defaults to gpx_video/ folder for both .gpx and video files
        :out_dir_path = defaults to ./out/
        """

        self.intersection_listDF = None
        self.intersection_load = None
        self.date_format = "%m-%d-%Y--%H-%M-%S.%f-%Z"
        self.pretty_datetime_format = "%y-%m-%d %H:%M:%S"

        self.in_dir_path = in_dir_path
        self.in_gpx_dir_path = in_gpx_dir_path
        self.out_dir_path = out_dir_path

        # init variables
        self.intersection_filename = signals_filename
        self.gpx_filename = gpx_filename
        self.pickle_file = ''
        self.gpx_file = ''
        self.csv_file = None
        self.gpxDF = ''
        self.gpx_listDF = None
        self.gDF_pickle_file = None

        self.sum_time_gap = 0.0
        self.sum_total_points = 0.0

        # scafold directory structure if not present
        gpx_video_dir = self.in_dir_path / self.in_gpx_dir_path
        p = Path(str(gpx_video_dir))

        if not p.is_dir():
            os.makedirs(gpx_video_dir, exist_ok=True)
            os.makedirs(self.out_dir_path, exist_ok=True)
            print(f"Created ./{self.in_dir_path} and ./{gpx_video_dir}/ directories for input files")
            print(f"Load formated CSV signal file to {self.in_dir_path}"
                  f"Load GPX dynamic route file to ./{gpx_video_dir}"
                  f"Load Video recording files to ./{gpx_video_dir}"
                  )

        all_intersections_df = self.load_intersection_csv(signals_filename)
        gpx_df = self.load_gpx_to_obj_df(gpx_filename, use_pickle=False)



    @staticmethod
    def speed_calc(point1, point2, t1, t2) -> float:
        """
        Calculates Meters Per Second speed between two point and time objects
        """
        # dist = geo.distance(point1.latitude, point1.longitude, point2.latitude, point2.longitude)
        dist = geodesic(point1, point2).meters
        time = (t2 - t1).total_seconds()  # timedelta converted to float

        if time > 0:
            speed = dist / time
            if speed < 50:  # 50 meters/sec threshold for accurate speed
                return speed
            else:
                return 0.0
        else:
            return 0.0

    def get_intersection_object_by_id(self, intersection_id):
        return self.intersection_listDF.iloc[intersection_id-1, 1]

    def intersection_frame_description(self, sro_id, b_index, distance, ts, desc_type="filename"):
        i_obj = self.get_intersection_object_by_id(sro_id)

        i_id = sro_id
        i_bearing = b_index
        i_compass_bearing = i_obj.get_bearing_str(b_index)
        i_name = i_obj.get_name()
        i_name_one = i_obj.get_name(0)
        i_name_two = i_obj.get_name(1)
        i_sd = i_obj.get_sd(b_index)
        i_dist = distance
        ts_utc = round(ts, 3)
        dt_temp = datetime.fromtimestamp(ts, tz=None)
        date_time = dt_temp.strftime("%a, %b %-d %Y at %I:%-M %p")

        #  don't use "/" when building filename string
        if desc_type == "filename":
            filename_desc = f'{i_id}.{i_bearing}-{i_name}-{i_sd}-{ts_utc}'
            return filename_desc
        elif desc_type == "label":
            label = f'{i_compass_bearing} approach of {i_name_one} and {i_name_two} (#{sro_id}) at ~{i_sd} ft on {date_time}'
            return label


    def load_intersection_csv(self, intersection_filename: str) -> pd.DataFrame:
        """ Loads CSV file into Intersection Class DataFrame

        :param intersection_filename: name of CSV file for loading (leave off .csv)
        :return: dataframe of intersections objects in each row
        """

        csv_intersection_file = PurePath(self.in_dir_path, intersection_filename + ".csv")
        self.intersection_load = {"id": [], "intersection_obj": []}

        with open(csv_intersection_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            line_count = 0
            for row in csv_reader:
                self.intersection_load["id"].append(int(row[0]))
                self.intersection_load["intersection_obj"].append(
                    Intersection(
                        # id_num
                        int(row[0]),
                        # name1(N/S), name2(E/W)
                        tuple((str(row[1]),
                               str(row[2]))),
                        # center of intersection location
                        geopy.Point(float(row[3]),
                                    float(row[4])),
                        # spd_N, spd_E, spd_S, spd_W
                        tuple((int(row[5]), int(row[6]), int(row[7]),
                               int(row[8]))),
                        # bearing_N, bearing_E, bearing_S, bearing_W
                        tuple((float(row[9]), float(row[10]), float(row[11]),
                               float(row[12]))),
                        # NB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        tuple((geopy.Point(row[13], row[14]),
                               geopy.Point(row[15], row[16]))),
                        # EB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        tuple((geopy.Point(row[17], row[18]),
                               geopy.Point(row[19], row[20]))),
                        # SB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        tuple((geopy.Point(row[21], row[22]),
                               geopy.Point(row[23], row[24]))),
                        # WB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        tuple((geopy.Point(row[25], row[26]),
                               geopy.Point(row[27], row[28])))
                    ))

                line_count += 1

            self.intersection_listDF = pd.DataFrame(self.intersection_load)
            print(
                f"Processed {line_count} lines of CSV file for a total of {len(self.intersection_listDF.index)} intersections."
            )
        return self.intersection_listDF

    def set_gpx_ver(self):
        gpx_string = etree.tostring(etree.parse(self.gpx_file), encoding=str)
        gpx_ver_10 = gpx_string.find("http://www.topografix.com/GPX/1/0")
        gpx_ver_11 = gpx_string.find("http://www.topografix.com/GPX/1/1")
        if gpx_ver_10 < 0 and gpx_ver_11 > 0:
            self.gpx_ver = "1.1"
            return self.gpx_ver
        else:
            self.gpx_ver = "1.0"
            return self.gpx_ver

    def load_gpx_to_obj_df(self, gpx_filename: str, gpx_ver = "1.0", use_pickle=True) -> pd.DataFrame:
        """ Loads GPX file into point objects and returns a dataframe of all the points
        """

        self.gpx_filename = gpx_filename
        self.gpx_ver = gpx_ver
        self.gpx_file = self.in_dir_path / self.in_gpx_dir_path / (gpx_filename + ".gpx")
        self.pickle_file = self.out_dir_path / (gpx_filename + ".pkl")
        self.csv_file = self.out_dir_path / (gpx_filename + ".csv")

        gpx_load = {"gpx_pt": []}

        # initialize starting variables if GPX v1.1 needs speed calcs
        pnt1 = geopy.Point()
        t1 = datetime.now(timezone.utc)

        if use_pickle and Path(self.pickle_file).is_file():
            self.gpxDF = pd.read_pickle(self.pickle_file)
            print(
                f"Loaded Pickle file {self.pickle_file} into Dataframe with {self.gpxDF.last_valid_index()} rows"
            )
        else:
            print(
                f"Using GPX file: {self.gpx_file}"
            )

        self.gpx_ver = self.set_gpx_ver()

        gpx_file_ref = open(self.gpx_file, "r")
        # use GPX v1.0, assume speed data otherwise will calculate
        # if speed is captured in GPX v1.1 as extension data, change version to 1.1
        # TODO: set timezone with lat, lon coordinates:
        #  (https://stackoverflow.com/questions/15742045/getting-time-zone-from-lat-long-coordinates)


        gpx = gpxpy.parse(gpx_file_ref, version=self.gpx_ver)
        pt_count = 0
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if self.gpx_ver == "1.1":
                        extra_data = {}
                        extension_data = {
                            lxml.etree.QName(child).localname: float(child.text)
                            for child in point.extensions[0]
                        }
                        for k, v in extension_data.items():
                            extra_data[k] = v

                        point.speed = extra_data["speed"]

                    p = geopy.Point(
                        latitude=point.latitude,
                        longitude=point.longitude,
                    )

                    if point.speed is not None:
                        pass    # GPX v1.0 includes speed in track, v1.1 can include in extension data
                    elif point.speed is None:  # GPX v1.1 speed calculation
                        if pt_count == 0:
                            point.speed = 0
                        else:
                            pnt0 = pnt1
                            pnt1 = p
                            t0 = t1
                            t1 = point.time

                            point.speed = self.speed_calc(pnt0, pnt1, t0, t1)

                    gpx_load["gpx_pt"].append(
                        GPXPoint(
                            pt_count,
                            str(point.time),  # convert ISO format point.time to a string for timestamp conversion
                            tuple(p),  # tuple of point, lat and lon
                            point.speed
                                 )
                    ) #  tuple for point for csv file output?.
                    pt_count += 1


        self.gpx_listDF = pd.DataFrame(gpx_load)
        self.gpx_listDF.to_pickle(self.pickle_file)
        self.gpx_listDF.to_csv(self.csv_file)
        print(
            f"Processed {pt_count} points of GPX file."
        )
        self.update_gpx_points()

        self.gpx_summary()


        return self.gpx_listDF

    def update_gpx_points(self):
        """
        updates gpx_prev_point and gpx_next_point as objects after the initial points
        are loaded
        """
        # simplify variable names
        last_index = self.gpx_listDF.last_valid_index()
        gpx_df = self.gpx_listDF
        cuml_d = 0.0

        # edge cases
        gpx_df.iloc[0, 0].set_next_gpx_point(gpx_df.iloc[1, 0])


        for i in range(1, last_index):  # populate prev_gpx_points
            gpx_df.iloc[i, 0].set_prev_gpx_point(gpx_df.iloc[i-1, 0])
        for i in range(last_index-1, 0, -1):  # reversed range to populate next_gpx_points
            gpx_df.iloc[i, 0].set_next_gpx_point(gpx_df.iloc[i+1, 0])

        # edge cases
        gpx_df.iloc[0, 0].set_next_gpx_point(gpx_df.iloc[1, 0])
        gpx_df.iloc[last_index, 0].set_prev_gpx_point(gpx_df.iloc[last_index - 1, 0])

        # repopulate prev_gpx_point objects so next_gpx_points are not NONE
        for i in range(1, last_index+1):
            current_gpx_pt = gpx_df.iloc[i, 0]
            current_gpx_pt.set_prev_gpx_point(gpx_df.iloc[i-1, 0])
            self.sum_time_gap += current_gpx_pt.get_prev_timedelta()
            cuml_d += current_gpx_pt.distance_to(current_gpx_pt.get_prev_gpx_point().get_location())
            current_gpx_pt.set_cumulative_distance(cuml_d)


        # edge cases again
        gpx_df.iloc[0, 0].set_next_gpx_point(gpx_df.iloc[1, 0])


        # display progress bar for calculating time-consuming backflow function
        for i in tqdm(range(len(gpx_df.index))):
            gpx_df.iloc[i, 0].backflow(self.intersection_listDF)

    def get_start_timestamp(self):
        return self.gpx_listDF.iloc[0, 0].get_timestamp()

    def get_end_timestamp(self):
        last_index = self.gpx_listDF.last_valid_index()
        return self.gpx_listDF.iloc[last_index, 0].get_timestamp()

    def intersection_checks(self):
        gpx_df = self.gpx_listDF
        all_intersections = self.intersection_listDF

        intersection_sd = []  # store intersection id & index in list
        intersection_ts = []  # store timestamps in list

        for point in range(len(gpx_df.index)):
            intersections_info = gpx_df.iloc[point, 0].get_intersection_approach_list()
            if intersections_info:
                p = gpx_df.iloc[point, 0]
                intersection_id, bearing_index, dist, approach = zip(*intersections_info)
                for item in range(len(list(intersection_id))):
                    sro_id = int(list(intersection_id)[item])
                    b_index = int(list(bearing_index)[item])
                    d_current = list(dist)[item]

                    approach_intersection = all_intersections.iloc[sro_id-1, 1]  # shift down by 1 for list
                    approach_intersection_sight_distance = approach_intersection.get_sd(b_index)

                    prev_p = p.get_prev_gpx_point()
                    next_p = p.get_next_gpx_point()
                    if prev_p is not None:
                        d_prev = p.get_prev_gpx_point().distance_to(approach_intersection.get_location())
                    if next_p is not None:
                        d_next = p.get_prev_gpx_point().distance_to(approach_intersection.get_location())

                    if p.h_prev_and_current_before_next(approach_intersection, b_index) and \
                       p.h_next_less_than_current(approach_intersection, b_index):

                        t_acc = p.t_to_approach_acc(approach_intersection, b_index)
                        print(
                            f"Signal #{sro_id}.{b_index} at {approach_intersection_sight_distance} ft")

                        t_shift_acc = p.get_timestamp() + t_acc
                        intersection_sd.append(self.intersection_frame_description(sro_id, b_index, d_current, t_shift_acc))
                        intersection_ts.append(t_shift_acc)

        z = zip(intersection_sd, intersection_ts)
        id_ts = list(z)
        ret = sorted(id_ts, key=lambda x: x[1])

        return ret


    @staticmethod
    def hr_min_sec(sec):
        if sec < 60:
            return f'{sec} seconds'
        elif sec < 3600:
            min = int(sec/60)
            sec_remain = round(sec - min * 60, 2)
            return f'{min}:{sec_remain} (MM:SS.ss)'
        elif sec >= 3600:
            hr = int(sec/3600)
            min = int(sec/60)
            sec_remain = round(sec - min * 60, 2)
            return f'{hr}:{min}:{sec_remain} (HH:MM:SS.ss)'

    @staticmethod
    def simplify_distance(d_ft):
        if d_ft < 5280:
            return f'{round(Distance(feet=d_ft).ft, 2)} feet'
        else:
            return f'{round(Distance(feet=d_ft).miles, 2)} miles'

    def gpx_summary(self):
        gpx_df = self.gpx_listDF
        last_index = gpx_df.last_valid_index()
        self.sum_total_points = last_index + 1  # pd dataframe starts at zero
        avg_time_gap = round(self.sum_time_gap / self.sum_total_points, 2)
        tot_sec = round(self.get_end_timestamp() - self.get_start_timestamp(), 2)
        tot_distance = gpx_df.iloc[last_index, 0].get_cumulative_distance()

        # display values
        width = int(70)
        title = "GPX SUMMARY"
        symbol = "-"

        summary = f"""
        {symbol * width}
        {" " * (int(width/2)-int(len(title)/2))}{title}
        {symbol * width}
        # GPX File:: {self.gpx_file}
        # Using GPX version: {self.gpx_ver}
        # Start time: {datetime.fromtimestamp(self.get_start_timestamp(), tz=None)}
        # End time:   {datetime.fromtimestamp(self.get_end_timestamp(), tz=None)}
        # Total duration: {self.hr_min_sec(tot_sec)}
        # Total distance: {self.simplify_distance(tot_distance)}
        # Number of data points: {self.sum_total_points}
        # Avg. Time Gap between data points: {avg_time_gap} Seconds
        {symbol * width}
        """
        # TODO:
        # difference in GPX and Video file start times and lengths of times
        # Number of images captured:
        # Number of intersections captures: X/ Total intersections (xx.x%)
        # Number of approaches captured
        # Approaches captures for duration of GPX file and Video File -> (images/time) (productivity ratio)
        # -------------------------------------------------------------------------------

        print(summary)







