# !/usr/bin/env python
# coding: utf-8
import os
import time
import datetime
from datetime import datetime
from pathlib import PurePath
from tqdm import tqdm

import geopy
import geopy.distance

import gpxpy.geo as gpxgeo

import numpy as np
import pandas as pd

from ssoss.static_road_object import Intersection, StaticRoadObject


class DynamicRoadObject:

    def __init__(self, id_num, name, obj_type, sro_df, gpx_df, source="GPX"):
        """Dynamic Road Objects move through time and space using a source (typ. GPX)

        :param id_num: unique ID number for object
        :param name: name for dynamic object
        :param obj_type: type of dynamic object (vehicle, ship, drone, etc.)
        :param sro_df: dataframe of static road objects
        :param gpx_df: dataframe of gpx points
        :param source: default to GPX, but in future could be a live stream of GPS data
        """

        self.MStoMPH = 2.23694
        self.FTPStoMPH = 0.681818
        self.MPHtoFTPS = 1/self.FTPStoMPH
        self.MStoFTPS = self.MStoMPH * self.MPHtoFTPS
        self.DATE_FORMAT = '%m-%d-%Y--%H-%M-%S.%f-%Z'

        # self.sorted_sroDF = None

        self.id_num = id_num
        self.name = name
        self.obj_type = obj_type
        self.gpx_df = gpx_df
        self.t0 = gpx_df.loc[0].t
        self.t1 = gpx_df.loc[1].t
        self.pnt0 = gpx_df.loc[0].geo_point
        self.pnt1 = gpx_df.loc[1].geo_point

        self.pt0 = geopy.Point(self.pnt0.latitude, self.pnt0.longitude)
        self.pt1 = geopy.Point(self.pnt1.latitude, self.pnt1.longitude)
        self.spd = gpx_df.loc[0].spd

        self.bearing = 0
        self.source = source

        self.sro_df = sro_df
        self.sorted_sroDF = None
        self.closest_intersection = self.get_closest_intersection(as_list=False)
        self.closest_intersection_list = self.get_closest_intersection(as_list=True)
        self.closest_approaching_intersection = self.get_closest_approaching_intersection(
        )

        self.in_file_path = PurePath("./in/")
        self.out_file_path = PurePath("./out/")

        if self.spd is None:
            self.calculate_spd_values()

    @staticmethod
    # https://stackoverflow.com/questions/11869910/pandas-filter-rows-of-dataframe-with-operator-chaining
    def mask(df, key, value) -> pd.DataFrame:
        return df[df[key] == value]

    def update_location_simple(self, i=2):
        """ Update dynamic object location with new data point i
        """
        self.t0 = self.t1
        self.t1 = self.gpx_df.loc[i].t

        self.pnt0 = self.pnt1
        self.pnt1 = self.gpx_df.loc[i].geo_point

        self.pt0 = self.pt1
        self.pt1 = geopy.Point(self.pnt1.latitude, self.pnt1.longitude)

        self.spd = self.gpx_df.loc[i].spd

        self.closest_intersection = self.get_closest_intersection()
        self.closest_approaching_intersection = self.get_closest_approaching_intersection()

    def first_timestamp(self) -> pd.Timestamp:
        t = datetime.fromisoformat(str(self.t0))
        return pd.Timestamp(t)

    def current_timestamp(self) -> pd.Timestamp:
        t = datetime.fromisoformat(str(self.t1))
        return pd.Timestamp(t)

    def first_utc_timestamp(self):
        t = self.t0.timetuple()
        return time.mktime(t) - 28800

    def get_prev_utc_timestamp(self) -> float:
        t = self.t0.timetuple()
        return time.mktime(t) - 28800

    def get_utc_timestamp(self) -> float:
        t = self.t1.timetuple()
        return time.mktime(t) - 28800

    @staticmethod
    def utc_to_timestamp(t):
        return time.asctime(time.localtime(t))

    def get_time_step(self):
        time_step = self.t1 - self.t0
        if time_step.total_seconds() < 0:
            return 10.0  # assume larger first gpx point time step
        else:
            return time_step.total_seconds()

    def get_location(self, i=None, elev=False):
        if elev:
            if i is None:
                return self.pnt1.format_decimal()
            else:
                self.update_location_simple(i)
                return self.pnt1.format_decimal()
        else:
            if i is None:
                return self.pt1.format_decimal()
            else:
                self.update_location_simple(i)
                return self.pt1.format_decimal()

    def get_dist_step(self) -> geopy.distance:
        """ first distance step

        :return: geopy distance in feet
        """
        return geopy.distance.distance(self.pt0, self.pt1).ft

    @staticmethod
    def get_dist_step_from_points(point1, point2) -> geopy.distance:
        """distance between two points in feet.

        :param point1: geopy point 1
        :param point2: geopy point 2
        :return: geopy distance in feet
        """

        return geopy.distance.distance(point1, point2).ft

    def cur_dist_to_sro(self, sro: StaticRoadObject) -> geopy.distance:
        if sro is None:
            return None
        else:
            return geopy.distance.distance(self.pt1, sro.get_location()).ft

    def prev_dist_to_sro(self, sro: StaticRoadObject) -> geopy.distance:
        if sro is None:
            return None
        else:
            return geopy.distance.distance(self.pt0, sro.get_location()).ft

    def get_spd(self, units="MPH") -> float:
        if units == "MPH":
            return float(self.spd * self.MStoMPH) # Ft/sec
        else:
            return float(self.spd)  # Meters/sec

    # Still necessary?
    def calculate_spd_values(self):
        """
        Loads speed values for all gpx_df items into a spd_list.

        This might be used if GPX v1.1 does not log speed data, so this will calculate it.
        """
        self.gpx_df.drop(['spd'], axis=1)  # remove None values for speed
        spd_list = [0]

        for n in range(1, self.gpx_df.last_valid_index()):
            self.update_location_simple(n)
            if self.get_time_step() == 0:
                speed = 0
            else:
                speed = (self.get_dist_step() /
                         self.get_time_step()) * self.FTPStoMPH

            spd_list.append(speed)
            if n == self.gpx_df.last_valid_index():
                self.gpx_df['spd'] = spd_list

    def get_bearing(self) -> float:
        b = gpxgeo.get_course(self.pt0[0], self.pt0[1], self.pt1[0], self.pt1[1])
        self.bearing = b
        return b

    def approaching(self, sro: StaticRoadObject) -> bool:  # , self.sro: StaticRoadObject
        if self.cur_dist_to_sro(sro) <= self.prev_dist_to_sro(sro):
            return True
        else:
            return False

    def get_closest_intersection(self, as_list=False) -> Intersection:
        """returns None or 1st or ascending sorted list of intersection objects based on distance
        """

        # Crop min and max distances to limit search, sort and length
        min_sd = self.sro_df.iloc[0, 1].get_sd("min")
        max_sd = self.sro_df.iloc[0, 1].get_sd("max")

        for row in range(0, self.sro_df.last_valid_index()):
            self.sro_df.loc[row,
                            "d"] = self.cur_dist_to_sro(self.sro_df.iloc[row, 1])
            self.sro_df.loc[row, "approaching"] = self.approaching(
                self.sro_df.iloc[row, 1])

        self.sorted_sroDF = self.sro_df.sort_values(by=['d'], ignore_index=True)

        min_row = self.sorted_sroDF[self.sorted_sroDF['d'].ge(min_sd)].index

        if len(min_row) == 0:
            min_row = 0
        else:
            min_row = min(min_row)

        max_row = self.sorted_sroDF[self.sorted_sroDF['d'].le(max_sd)].index
        if len(max_row) == 0:
            max_row = 0
        else:
            max_row = max(max_row) + 1  # +1 for inclusive

        limited_df = self.sorted_sroDF[min_row:max_row]

        if limited_df.empty:
            return None
        else:
            if as_list:
                return limited_df
            else:
                return limited_df.iloc[0, 1]

    def get_closest_approaching_intersection(self, as_list=False) -> Intersection:
        """ returns the closest, approaching intersection object for the current point
        of the dynamic object based on sorted list of intersections.

        :return: intersection object
        """
        df = self.get_closest_intersection(as_list=True)
        if df is None:
            return None
        else:
            mask = df['approaching'].values == True
            if df[mask].empty:
                return None
            elif as_list:
                return df[mask]
            elif as_list == False:
                return df[mask].iloc[0, 1]

    def calc_bearing_diff(self, m: float) -> float:
        n = self.get_bearing()
        b = min(abs(n - m), abs(360 - n + m), abs(360 - m + n))
        return b

    def approach_leg(self, itrsxn: Intersection, index_out=True):
        """determines the approach leg of the intersection based on compass headings

        :param itrsxn: intersection object to find approach leg of
        :param index_out: when True returns integer index, false returns string.
        :return: index of leg being approached of intersection based on bearing
             "True" index_out: 0 - North, 1 - East, 2 - South, 3 - West
             "False" index_out returns strings:  "NB","EB", "SB", "WB".
        """

        veh_int_diff = [
            self.calc_bearing_diff(itrsxn.get_bearing(0)),
            self.calc_bearing_diff(itrsxn.get_bearing(1)),
            self.calc_bearing_diff(itrsxn.get_bearing(2)),
            self.calc_bearing_diff(itrsxn.get_bearing(3))
        ]

        approach_leg_index = np.argmin(veh_int_diff)
        app_leg_dir = ""
        if itrsxn is None:
            return None
        elif index_out:
            return int(approach_leg_index)
        else:
            if approach_leg_index == 0:
                app_leg_dir = "NB"
            elif approach_leg_index == 1:
                app_leg_dir = "EB"
            elif approach_leg_index == 2:
                app_leg_dir = "SB"
            elif approach_leg_index == 3:
                app_leg_dir = "WB"
            return app_leg_dir

    def drive_gpx(self, gpx_filename: str, use_pickle_file=False) -> pd.DataFrame:
        """ Load the GPX file into a dataframe with timestamp, location, speed, dist to event, bearing, and
        id of approaching intersection

        :param gpx_filename: absolute filepath of file (without .gpx or .p file)
        :param use_pickle_file: default to False, can be faster to load from pickle
        :return: DataFrame with GPX file loaded and saves a CSV and Pickle file of gpx information
        """

        # gpx_file = PurePath(self.in_file_path, gpx_filename + ".gpx")
        pickle_file = self.out_file_path / (str(gpx_filename) + ".pkl")
        csv_file = self.out_file_path / (str(gpx_filename) + ".csv")

        approach_log_df = None

        if use_pickle_file and os.path.isfile(pickle_file):
            approach_log_df = pd.read_pickle(pickle_file)
            return approach_log_df
        else:
            # dictionary-> Keys:Values
            appr_dict = {
                "id": [],
                "appr_dir": [],
                "timestamp": [],
                "location": [],
                "spd": [],
                "distance": [],
                "bearing": [],
                "approaching": []
            }

            for i in range(2, self.gpx_df.last_valid_index()):
                self.update_location_simple(i)
                cai = self.get_closest_approaching_intersection()
                if cai is None:
                    if i == self.gpx_df.last_valid_index() - 1:
                        approach_log_df = pd.DataFrame(appr_dict)
                        approach_log_df.to_csv(csv_file)
                        approach_log_df.to_pickle(pickle_file)
                        print(
                            f"exported data frame to CSV (in {csv_file}) and Pickle (in {pickle_file})"
                        )
                    else:
                        pass
                else:
                    approaching_sd = False
                    appr_distance = (cai.distance_from_sb(
                        self.get_location(), self.approach_leg(cai)) -
                                     cai.get_sd(self.approach_leg(cai)))

                    if appr_distance > 0:
                        approaching_sd = True

                    appr_dict["id"].append(cai.get_id_num())
                    appr_dict["appr_dir"].append(self.approach_leg(cai))
                    appr_dict["timestamp"].append(self.get_utc_timestamp())
                    appr_dict["location"].append(self.get_location())
                    appr_dict["spd"].append(self.get_spd())
                    appr_dict["distance"].append(appr_distance)
                    appr_dict["bearing"].append(self.get_bearing())
                    appr_dict["approaching"].append(approaching_sd)

                    if i == self.gpx_df.last_valid_index() - 1:
                        approach_log_df = pd.DataFrame(appr_dict)
                        approach_log_df.to_csv(csv_file)
                        approach_log_df.to_pickle(pickle_file)
                        print(
                            f"Exported dataframe to CSV ({csv_file}) and Pickle ({pickle_file})"
                        )
        return approach_log_df

    def drive_gpx_stop_bar(self,
                           gpx_filename,
                           use_pickle_file=True) -> pd.DataFrame:
        """ Load the GPX file into a dataframe with timestamp, location, speed, dist to event, bearing, and
        id of approaching intersection

        :param gpx_directory: file directory where .gpx file is for input
        :param gpx_filename: filename of .gpx file (without .gpx)
        :param out_file_directory: where output files are saved to (./out/)
        :param use_pickle_file: default to False, can be faster to load from pickle
        :return: DataFrame with GPX calculated for sro file and saved a CSV and Pickle file of gpx information

        """
        # self.gpx_filepath = gpx_directory + gpx_filename + ".gpx"
        pickle_file = self.out_file_path / (str(gpx_filename) + ".p")
        csv_file = self.out_file_path / (str(gpx_filename) + ".csv")

        approach_sb_log_df = None

        if use_pickle_file and os.path.isfile(pickle_file):
            approach_sb_log_df = pd.read_pickle(pickle_file)
            return approach_sb_log_df
        else:
            # dictionary-> Keys:Values
            appr_dict = {
                "id": [],
                "appr_dir": [],
                "timestamp": [],
                "time_delta": [],
                "location": [],
                "spd": [],
                "distance": [],
                "bearing": [],
                "approaching": []
            }

            for i in tqdm(range(2, self.gpx_df.last_valid_index()),
                          desc="Loading GPX:",
                          unit="GPX Points"):

                self.update_location_simple(i)
                cai = self.get_closest_approaching_intersection()
                if cai is None:
                    if i == self.gpx_df.last_valid_index() - 1:
                        approach_sb_log_df = pd.DataFrame(appr_dict)
                        approach_sb_log_df.to_csv(csv_file)
                        approach_sb_log_df.to_pickle(pickle_file)
                        print(
                            f"exported dataframe to CSV (in {csv_file}) and Pickle (in {pickle_file})"
                        )
                    else:
                        pass
                else:
                    approaching_sd = False
                    appr_distance = (cai.distance_from_sb(
                        self.get_location(), self.approach_leg(cai)) -
                                     cai.get_sd(self.approach_leg(cai)))
                    # print(f'{i}: {appr_distance}ft from {cai.get_name()}')
                    if appr_distance > 0:
                        approaching_sd = True

                    appr_dict["id"].append(cai.get_id_num())
                    appr_dict["appr_dir"].append(self.approach_leg(cai))
                    appr_dict["timestamp"].append(self.get_utc_timestamp())
                    appr_dict["time_delta"].append(self.get_time_step())
                    appr_dict["location"].append(self.get_location())
                    appr_dict["spd"].append(self.get_spd())
                    appr_dict["distance"].append(appr_distance)
                    appr_dict["bearing"].append(self.get_bearing())
                    appr_dict["approaching"].append(approaching_sd)

                    if i == self.gpx_df.last_valid_index() - 1:
                        print("WRITING DICT TO DATAFRAME")
                        approach_sb_log_df = pd.DataFrame(appr_dict)
                        approach_sb_log_df.to_csv(csv_file)
                        approach_sb_log_df.to_pickle(pickle_file)
                        print(
                            f"Exported data frame to CSV ({csv_file}) and Pickle ({pickle_file})"
                        )
                        print(f'ApproachSB_DF:{approach_sb_log_df}')

        return approach_sb_log_df

    def get_street(self, itrsxn: Intersection) -> str:
        """ current Street of intersection approach leg
        """
        apr_leg_index = self.approach_leg(itrsxn)
        return itrsxn.get_name(apr_leg_index)

    def get_info(self, itrsxn: Intersection) -> str:
        """ get ID#, bearing, and name about an intersection

        :param itrsxn: Intersection Object
        :return: string of info in format ID#.Compass_Heading - Intersection Name
        """
        return str(
            f'{itrsxn.get_id_num()}.{self.approach_leg(itrsxn)}-{itrsxn.get_name()}'
        )

    def get_itrsxn_obj_by_id(self, id_num: int) -> Intersection:
        """get intersection object from ID number.

        :param id_num: ID number of intersection object
        :return: intersection object
        """
        mask = self.sro_df['id'] == id_num
        return self.sro_df[mask].iloc[0, 1]

    def get_info_by_id(self, id_num: int, appr_dir) -> str:
        """get info about intersection

        :param id_num: ID # of intersection
        :param appr_dir: approach direction to intersection
        :return: string in format:
            ID#.direction_index - street1 + street2 - event distance string
        """
        mask = self.sro_df['id'] == id_num
        itrsxn = self.sro_df[mask].iloc[0, 1]
        """
        Example: 2.0-YVR+California-35mph-325ft-UTCtime
        Include: direction, Approach Posted Speed
        """
        return str(
            f'{itrsxn.get_id_num()}.{appr_dir}-{itrsxn.get_name()}-{itrsxn.get_sd(appr_dir)}ft'
        )

    @staticmethod
    def find_index(df, i):
        return df.iloc[i]

    @staticmethod
    def t_spd_adjust(d0, spd0, d1, spd1):
        """ Adjusts time of event based on speed of gpx points i and i+1.

        :param d0: distance a t=0
        :param spd0: speed at t=0
        :param d1: distance a t=1
        :param spd1: speed at t=1
        :return: time adjustment from t=0 to event location
        """
        t_adj0 = d0 / spd0
        t_adj1 = d1 / spd1

        d_step = d0 + abs(d1)

        w0 = d0 / d_step
        w1 = abs(d1) / d_step

        sum_t_adj = abs(w0 * t_adj0 + w1 * t_adj1)

        return sum_t_adj / 2.0

    def seek_sd(self, gpx_df, csv_out=True) -> pd.DataFrame:
        """Find event time of Sight Distance(sd) for each intersection traveled through

        :param gpx_df: dataframe of processed GPX file with SRO's events calculated
        :param csv_out: save a CSV file of the intersection and approaches captured
        :return: dataframe of intersection approaches and speed and distance
        """

        # How this method works:
        # i-1 -- Previous timestep gpx point (typically 1 second behind)
        # i   -- current timestep of gpx point
        # i+1 -- next timestep gpx point (typically 1 second ahead)
        # i+2 -- 2nd next timestep gpx point (typically 2 seconds ahead)

        # For each step in the GPS
        #  if speed(i) AND speed(i+1) > 0.4 mph AND distance to sight distance <=
        #   approaching intersection's sight distance + 50ft
        #   AND i-1 AND i are approaching intersection
        #   AND i+1 AND i+2 are not approaching (i.e. just passed event distance)

        # initialize dataframe of sighted intersections and misc. info
        df_dict = {
            "id": [],
            "appr_dir": [],
            "timestamp": [],
            "location": [],
            "spd": [],          # MPH
            "distance": [],     # FEET
            "t_adjust": [],     # SECONDS
            "string_desc": []
        }

        for i in range(1, (gpx_df.last_valid_index() - 3)):
            if gpx_df.spd.iloc[i] > 0.4 and \
                    gpx_df.spd.iloc[i + 1] > 0.4 and \
                    gpx_df.distance.iloc[i + 1] <= \
                    self.get_itrsxn_obj_by_id(gpx_df.id.iloc[i]).get_sd(gpx_df.appr_dir.iloc[i + 1]) + \
                        (gpx_df.time_delta.iloc[i] * (gpx_df.spd.iloc[i] * self.MPHtoFTPS)):
                print("heuristic filter")

                if (gpx_df.approaching.iloc[i - 1]) == True and \
                        (gpx_df.approaching.iloc[i]) == True and \
                        (gpx_df.approaching.iloc[i + 1] == False) and \
                        (gpx_df.approaching.iloc[i + 2] == False):

                    print("approach filter")

                    t_adjust = self.t_spd_adjust(gpx_df.distance.iloc[i], gpx_df.spd.iloc[i],
                                                 gpx_df.distance.iloc[i + 1], gpx_df.spd.iloc[i + 1]
                                                 )


                    # t_adj is less than timestep when dynamic object is close to event distance
                    if t_adjust <= gpx_df.time_delta.iloc[i]:
                        print("t-adjust filter")
                        df_dict["id"].append(gpx_df.id.iloc[i])
                        df_dict["appr_dir"].append(gpx_df.appr_dir.iloc[i])
                        df_dict["timestamp"].append(gpx_df.timestamp.iloc[i])
                        df_dict["location"].append(gpx_df.location.iloc[i])
                        df_dict["spd"].append(gpx_df.spd.iloc[i])
                        df_dict["distance"].append(gpx_df.distance.iloc[i])
                        df_dict["t_adjust"].append(t_adjust)
                        df_dict["string_desc"].append(
                            self.get_info_by_id(gpx_df.id.iloc[i],
                                                gpx_df.appr_dir.iloc[i]))
                        print(
                            f'seek_sd_Info:{self.get_info_by_id(gpx_df.id.iloc[i], gpx_df.appr_dir.iloc[i])}, time adjust:{t_adjust}'
                        )
                    else:
                        pass
            else:
                pass
        if csv_out:
            pd.DataFrame(df_dict).to_csv(
                self.out_file_path / "approaching_intersections.csv"
            )
        return pd.DataFrame(df_dict)

    # TODO: Ensure this works properly for Stop bar data, combine with seek_sd method
    def seek_sb(self, gpx_df, csv_out=True) -> pd.DataFrame:
        """Find event time of Stop Bar (sb)  for each intersection traveled through

        :param gpx_df: dataframe of GPX file
        :param csv_out: save a CSV file of the intersection and approaches captured
        :return: dataframe of intersection approaches and speed and distance
        """

        # See seek_sd for how this method works

        df_dict_sb = {
            "id": [],
            "appr_dir": [],
            "timestamp": [],
            "location": [],
            "spd": [],
            "distance": [],
            "t_adjust": [],
            "string_desc": []
        }

        for i in range(1, (gpx_df.last_valid_index() - 3)):
            if self.get_itrsxn_obj_by_id(gpx_df.id.iloc[i]).distance_from_sb(
                    gpx_df.location.iloc[i + 1], gpx_df.appr_dir.iloc[i + 1]) is None:
                print(f'USING CENTER OF INTERSECTION LOCATION')
                approach_distance = self.get_itrsxn_obj_by_id(
                    gpx_df.id.iloc[i]).get_sd(gpx_df.appr_dir.iloc[i + 1]) + 50
            else:
                print(f'USING STOP BAR LOCATION')
                approach_distance = self.get_itrsxn_obj_by_id(
                    gpx_df.id.iloc[i]).distance_from_sb(gpx_df.location.iloc[i + 1],
                                                        gpx_df.appr_dir.iloc[i + 1])

            if gpx_df.spd.iloc[i] > 0.2 and gpx_df.spd.iloc[i + 1] > 0.2 \
                    and gpx_df.distance.iloc[i + 1] <= approach_distance <= gpx_df.distance.iloc[i]:

                if True:
                    """
                    calculate exact time based on speed. using i and i+1. 
                    
                    For point i and i+1, the exact time adjustment is weighted
                    based on the speeds at these two point's in time. This shifts the exact position
                    of the car to the most accurate time it was at the calculated sight distance
                    
                    store that time in UTC in DF
                    """

                    t_adjust = self.t_spd_adjust(gpx_df.distance.iloc[i], gpx_df.spd.iloc[i],
                                                 gpx_df.distance.iloc[i + 1], gpx_df.spd.iloc[i + 1]
                                                 )

                    if t_adjust <= 1:
                        df_dict_sb["id"].append(gpx_df.id.iloc[i])
                        df_dict_sb["appr_dir"].append(gpx_df.appr_dir.iloc[i])
                        df_dict_sb["timestamp"].append(gpx_df.timestamp.iloc[i])
                        df_dict_sb["location"].append(gpx_df.location.iloc[i])
                        df_dict_sb["spd"].append(gpx_df.spd.iloc[i])
                        df_dict_sb["distance"].append(gpx_df.distance.iloc[i])
                        df_dict_sb["t_adjust"].append(t_adjust)
                        df_dict_sb["string_desc"].append(
                            self.get_info_by_id(gpx_df.id.iloc[i],
                                                gpx_df.appr_dir.iloc[i]))

                        # print(self.utc_to_timestamp(df.timestamp.iloc[i]))
                        print(
                            f'info:{self.get_info_by_id(gpx_df.id.iloc[i], gpx_df.appr_dir.iloc[i])}'
                        )

                    else:
                        pass
            else:
                pass
        if csv_out:
            pd.DataFrame(df_dict_sb).to_csv(
                self.out_file_path / "approaching_intersections_Stopbar.csv")
        return pd.DataFrame(df_dict_sb)

    # TODO: create new method
    # def get_info_at_timestamp(timestamp)
    #   return intersection ID, approach, spd, distance, compass direction, lat, lon


class Vehicle(DynamicRoadObject):
    pass
