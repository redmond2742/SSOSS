# !/usr/bin/env python
# coding: utf-8
import math
from datetime import datetime, timezone
from datetime import timedelta
from operator import attrgetter, itemgetter
from pathlib import PurePath

import dateutil
import geopy
import gpxpy.geo as gpxgeo
import numpy as np
import pandas as pd

from ssoss.static_road_object import StaticRoadObject, Intersection


class GPXPoint:
    """class for GPX points to calculate necessary distances and positions to other objects
    """

    def __init__(self, id_num: int, t, p: geopy.Point, spd: float):
        """ TODO: do we need a timezone parameter?

        :param id_num: count number of point in GPX file
        :param t: timestamp of gpx point
        :param pt: geopy point, longitude and latitude of point
        :param spd: speed in ft/sec at that point
        """
        # constants for unit conversions
        self.MStoMPH = 2.23694
        self.FTPStoMPH = 0.681818
        self.MPHtoFTPS = 1 / self.FTPStoMPH
        self.MStoFTPS = self.MStoMPH * self.MPHtoFTPS


        # initial variables from GPX file

        self.id = id_num
        t_temp = (dateutil.parser.isoparse(t))
        self.t = t_temp.replace(tzinfo=timezone.utc).timestamp()
        self.p = geopy.Point(p[0], p[1])  # elevation not supported
        self.spd = spd

        # calculated variables from backflow function
        self.prev_gpx_point = None  # GPX Class Object
        self.next_gpx_point = None  # GPX Class Object
        self.bearing = None

        # advanced calculated
        self.intersection_approach_list = None
        self.cumulative_distance = 0.0
        #self.closest_intersection_list = None                # sorted list
        #self.approaching_intersection_list = None            # dict:  #   True/False
        #self.closest_approaching_intersection = None    # sorted list
        # self.approach_leg(intersection_ID)        # index value
        # self.sight_distance(leg, intersection_id) # distance in feet



    def get_id(self) -> int:
        return self.id

    def get_timestamp(self) -> datetime:
        return self.t

    def get_prev_timedelta(self) -> float:
        return self.t - self.prev_gpx_point.get_timestamp()

    def get_next_timedelta(self) -> float:
        return self.next_gpx_point.get_timestamp() - self.t

    def get_location(self) -> geopy.Point:
        return self.p

    def get_intersection_approach_list(self):
        return self.intersection_approach_list

    def distance_to(self, p1) -> geopy.distance:
        return geopy.distance.distance(p1, self.p).ft

    def get_dist_between_points(self, p1, p2) -> geopy.distance:
        return geopy.distance.distance(p1, p2).ft

    def get_cumulative_distance(self):
        return self.cumulative_distance  # Feet

    def get_speed(self, units="ft_per_sec") -> float:
        """
        speed from gpx is meters/second
        :return: speed in ft/second
        """
        if units == "ft_per_sec":
            return self.spd * self.MStoFTPS

    def get_prev_gpx_point(self):
        return self.prev_gpx_point  # GPX Point Object

    def get_next_gpx_point(self):
        return self.next_gpx_point  # GPX Point Object

    def set_prev_gpx_point(self, o):
        self.prev_gpx_point = o

    def set_next_gpx_point(self, o):
        self.next_gpx_point = o

    def set_cumulative_distance(self, d):
        self.cumulative_distance = d

    def is_intersection_in_next_point(self, i, b) -> bool:
        out_bool = False
        next_intersection_appr_list = self.next_gpx_point.get_intersection_approach_list()

        if next_intersection_appr_list:
            id_list, b_index, dist, appr = zip(*next_intersection_appr_list)
            for x in range(len(list(id_list))):
                if i == id_list[x] and b == b_index[x]:
                    out_bool = True

        return out_bool

    def approaching(self, sro: StaticRoadObject) -> bool:
        if self.prev_gpx_point is None:
            return False
        elif self.distance_to(sro.get_location()) < self.prev_gpx_point.distance_to(sro.get_location()):
            return True
        else:
            return False

    def get_bearing(self) -> float:
        if self.prev_gpx_point is None:
            return 0
        else:
            prev_lat = self.prev_gpx_point.get_location().latitude
            prev_lon = self.prev_gpx_point.get_location().longitude
            cur_lat = self.get_location().latitude
            cur_lon = self.get_location().longitude

            self.bearing = gpxgeo.get_course(prev_lat, prev_lon, cur_lat, cur_lon)
            return self.bearing

    def calc_bearing_diff(self, m: float) -> float:
        n = self.get_bearing()
        b_diff = min(abs(n - m), abs(360 - n + m), abs(360 - m + n))
        return b_diff

    def get_approach_leg(self, intersection: Intersection, index_out=True):
        """determines the approach leg of the intersection based on compass headings

        :param intersection: intersection object to find approach leg of
        :param index_out: when True returns integer index, false returns string.
        :return: index of leg being approached of intersection based on bearing
               "True" index_out: 0 - North, 1 - East, 2 - South, 3 - West
               "False" index_out returns strings:  "NB","EB", "SB", "WB".
        """

        pt_to_intersection_diff = [
            self.calc_bearing_diff(intersection.get_bearing(0)),
            self.calc_bearing_diff(intersection.get_bearing(1)),
            self.calc_bearing_diff(intersection.get_bearing(2)),
            self.calc_bearing_diff(intersection.get_bearing(3))
        ]

        approach_leg_index = np.argmin(pt_to_intersection_diff)
        approach_leg_string = ""

        if intersection is None:
            return None
        elif index_out:
            return int(approach_leg_index)
        else:
            if approach_leg_index == 0:
                approach_leg_string = "NB"
            elif approach_leg_index == 1:
                approach_leg_string = "EB"
            elif approach_leg_index == 2:
                approach_leg_string = "SB"
            elif approach_leg_index == 3:
                approach_leg_string = "WB"
            return approach_leg_string

    def t_to_approach_simple(self, approaching_intersection: Intersection, b_index: int) -> float:
        d = self.distance_to(approaching_intersection.get_location()) - approaching_intersection.get_sd(b_index)
        if self.get_speed() > 0:
            return d / self.get_speed()
        else:
            return 0

    def acceleration(self) -> float:

        if self.get_next_gpx_point() is not None and self.get_next_timedelta is not None:
            t_delta = self.get_next_timedelta()
            v_initial = self.get_speed()
            v_final = self.get_next_gpx_point().get_speed()
            return (v_final - v_initial) / t_delta

        else:
            return 0.0

    def t_to_approach_acc(self, approaching_intersection: Intersection, b_index: int) -> float:
        approach_i_sd = approaching_intersection.get_sd(b_index)
        d_sd = self.distance_to(approaching_intersection.get_location()) - approach_i_sd

        # radical: sqrt(v^2 - 4 * acc * d_sd)
        if self.get_speed()**2 > 4 * self.acceleration() * d_sd:
            radical = math.sqrt(self.get_speed()**2 - 4 * self.acceleration() * d_sd)
        else:
            radical = 0
        # denominator: 2 * acc
        denominator = 2*self.acceleration()

        if denominator == 0 or d_sd <= 0:
            return self.t_to_approach_simple(approaching_intersection, b_index)
        else:
            t_acc_pos = (-self.get_speed() + radical) / denominator
            t_acc_neg = (-self.get_speed() - radical) / denominator
            return min(abs(t_acc_neg), abs(t_acc_pos))

    def backflow(self, sro_df: pd.DataFrame):
        """
        after initial GPX points loaded, used intersection dataframe objects to calculate
        values of interest.

        :param sro_df: static road object loaded as dataframe.
        :return:
        """
        # empty lists
        intersection_id = []
        approach_leg = []
        dist = []
        approaching = []

        for index, row in sro_df.iterrows():
            intersection = row["intersection_obj"]
            distance_to_intersection = self.distance_to(intersection.get_location())
            # TODO: consider add min trim also?
            if distance_to_intersection > intersection.get_sd("max"):  # only load relevant distances
                pass
            else:
                intersection_id.append(intersection.get_id_num())
                approach_leg.append(self.get_approach_leg(intersection))
                dist.append(distance_to_intersection)
                approaching.append(self.approaching(intersection))

        temp_all_lists = zip(intersection_id, approach_leg, dist, approaching)
        temp_sort_distance = sorted(temp_all_lists, key=itemgetter(2))  # sort by item 2/distance
        temp_sort_approaching = sorted(temp_sort_distance, key=itemgetter(3), reverse=True)  # sort by item 3/approaching boolean
        only_approaching_intersections = filter(lambda x: x[3] is True, temp_sort_approaching)  # filter out intersections not approached
        self.intersection_approach_list = list(only_approaching_intersections)

        return;
    #  heuristic: d0 and d1 upstream from sight distance (X), d2 downstream of sight distance(X)
    #  -d0-------d1----X-----d2------0
    def h_prev_and_current_before_next(self, approaching_intersection: Intersection, b_index: int) -> bool:
        h_flag = False
        p_prev = self.get_prev_gpx_point()
        p_next = self.get_next_gpx_point()

        approach_i_sd = approaching_intersection.get_sd(b_index)

        d0 = p_prev.distance_to(approaching_intersection.get_location())
        d1 = self.distance_to(approaching_intersection.get_location())
        if p_next is not None:
            d2 = p_next.distance_to(approaching_intersection.get_location())
        else:
            d2 = 0

        if d0 >= approach_i_sd:
            if d1 >= approach_i_sd:
                if d2 <= approach_i_sd:
                    h_flag = True

        return h_flag

    #  heuristic: d2 less than d1
    #  -d1---X----d2------0
    def h_next_less_than_current(self, approaching_intersection: Intersection, b_index: int) -> bool:
        h_flag = False
        p_next = self.get_next_gpx_point()
        approach_i_sd = approaching_intersection.get_sd(b_index)
        d1 = abs(self.distance_to(approaching_intersection.get_location()))
        if p_next is not None:
            d2 = abs(p_next.distance_to(approaching_intersection.get_location()) - approach_i_sd)
        else:
            d2 = 0

        if d2 <= d1:
            h_flag = True

        return h_flag



    # TODO: consider developing heuristic based on --d0----d1----X---0  without a next_d available
    # TODO: consider developing heuristic based on narrowing based on approach angle





