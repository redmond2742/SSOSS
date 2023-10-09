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
from icecream import ic


class GPXPoint:
    """class for GPX points to calculate necessary distances and positions to other objects
    """

    def __init__(self, id_num: int, t, p: geopy.Point, spd: float):
        """

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
        self.veh_gap = 0.0
        

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
        self.generic_so_approach_list = None
        self.generic_so_list = None
        self.cumulative_distance = 0.0

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
    
    def get_generic_so_approach_list(self):
        return self.generic_so_approach_list

    def get_intersection_approach_list(self):
        return self.intersection_approach_list

    def distance_to(self, p1) -> geopy.distance:
        return geopy.distance.distance(p1, self.p).ft
    
    def distance_to_line(self, p1, p2) -> float:
        a = geopy.distance.distance(p1, p2).ft
        b = geopy.distance.distance(p1, self.get_location()).ft
        c = geopy.distance.distance(p2, self.get_location()).ft
        if a is not None and b is not None and c is not None:
            s = (a + b + c) / 2
            dist_to_sb = 2. * math.sqrt(abs(s * (s -a) * (s - b) * (s - c))) / a
            return dist_to_sb
        else:
            return 0

    def get_dist_between_points(self, p1, p2) -> geopy.distance:
        return geopy.distance.distance(p1, p2).ft
    
    def get_dist_to_prev_point(self) -> geopy.distance:
        return geopy.distance.distance(self.prev_gpx_point.get_location(), self.p).ft
    
    def get_dist_to_next_point(self) -> geopy.distance:
        return geopy.distance.distance(self.p, self.next_gpx_point.get_location()).ft

    def get_cumulative_distance(self):
        return self.cumulative_distance  # Feet

    def get_speed(self, units="ft_per_sec") -> float:
        """
        speed from gpx is meters/second
        :return: speed in ft/second
        """
        if units == "ft_per_sec":
            speed = self.spd * self.MStoFTPS

        return speed

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
        """determine difference between angles"""
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

    def t_to_approach_simple(self, approaching_intersection:Intersection, b_index: int) -> float:
        
        approach_i_sb_pt1 = approaching_intersection.stop_bar_d[b_index][0]
        approach_i_sb_pt2 = approaching_intersection.stop_bar_d[b_index][1]
        
        if (not approaching_intersection.all_sb_line_available()):
            d = self.distance_to(approaching_intersection.get_location()) - approaching_intersection.get_sd(b_index)
        else:
            d = self.distance_to(approaching_intersection.get_location()) \
                  - approaching_intersection.get_sd(b_index)              
        
        
        if self.get_speed() > 0:
            return d / self.get_speed()
        else:
            return 0
    
    def t_to_generic_so_simple(self, generic_so) -> float:
        generic_so_dist = generic_so.get_sd()
        d = self.distance_to(generic_so.get_location()) - generic_so_dist

        if self.get_speed() > 0:
            return d / self.get_speed()
        else:
            return 0
        
    def acceleration(self) -> float:
        """ acceleration calculation between two GPX points"""

        if self.get_next_gpx_point() is not None and self.get_next_timedelta is not None:
            t_delta = self.get_next_timedelta()
            v_initial = self.get_speed()
            v_final = self.get_next_gpx_point().get_speed()
            return (v_final - v_initial) / t_delta
        else:
            return 0.0
        
    def t_to_generic_so_acc(self, generic_so) -> float:
        generic_so_dist = generic_so.get_sd()
        d_sd = d_sd_simple = self.distance_to(generic_so.get_location()) - generic_so_dist
        
        # radical: sqrt(v^2 - 4 * acc * d_sd)
        if self.get_speed()**2 > 4 * self.acceleration() * d_sd:
            radical = math.sqrt(self.get_speed()**2 - 4 * self.acceleration() * d_sd)
        else:
            radical = 0
        # denominator: 2 * acc
        denominator = 2*self.acceleration()

        if denominator == 0 or d_sd <= 0:
            return self.t_to_generic_so_simple(generic_so) #create method
        else:
            t_acc_pos = (-self.get_speed() + radical) / denominator
            t_acc_neg = (-self.get_speed() - radical) / denominator
            return min(abs(t_acc_neg), abs(t_acc_pos))



    def t_to_approach_acc(self, approaching_intersection:Intersection, b_index: int) -> float:
        
        approach_i_sd = approaching_intersection.get_sd(b_index)

        approach_i_sb_pt1 = approaching_intersection.stop_bar_d[b_index][0]
        approach_i_sb_pt2 = approaching_intersection.stop_bar_d[b_index][1]
        
        d_sd_simple = self.distance_to(approaching_intersection.get_location()) - approach_i_sd

        if (not approaching_intersection.all_sb_line_available()):
            d_sd = self.distance_to(approaching_intersection.get_location()) - approach_i_sd
        else:
            d_sd = self.distance_to(approaching_intersection.get_location()) - approach_i_sd
            print(f"t_to_approach, d_sd_simple:{d_sd_simple}, d_sd_hd{d_sd}")
            

        
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

    def backflow(self, sro_df: pd.DataFrame, so_type):
        """
        after initial GPX points loaded, used intersection dataframe objects to calculate
        values of interest.

        :param sro_df: static road object loaded as dataframe.
        :return:
        """
        if so_type == "intersection":
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
        
        elif so_type == "generic_so":
            #empty lists
            generic_so_id = []
            dist = []
            approaching = []
            buffer_dist = 150 #ft of buffer to add to static object sight distance

            count = 0
            for index, row in sro_df.iterrows():
                generic_so = row["generic_so_obj"]
                distance_to_generic_so = self.distance_to(generic_so.get_location())
                if distance_to_generic_so > generic_so.get_sd() + buffer_dist:
                    pass
                else:
                    generic_so_id.append(generic_so.get_id_num())
                    dist.append(distance_to_generic_so)
                    approaching.append(self.approaching(generic_so))
            
            temp_all_lists = zip(generic_so_id, dist, approaching)
            temp_sort_distance = sorted(temp_all_lists, key=itemgetter(1))  # sort by item 1/distance
            temp_sort_approaching = sorted(temp_sort_distance, key=itemgetter(2), reverse=True)  # sort by item 2/approaching boolean
            only_approaching_generic_so = filter(lambda x: x[2] is True, temp_sort_approaching)  # filter out generic_so not approached
            self.generic_so_approach_list = list(only_approaching_generic_so)

        return;

    def three_pt_approach(self,d0, d1, d2, approach_distance) -> bool:
        """ check if d0 & d1 points are before approach distance and d2 is after"""
        if d0 >= approach_distance:
            if d1 >= approach_distance:
                if self.get_dist_to_next_point() > approach_distance: #account for small sight distances
                    return True
                elif d2 <= approach_distance:
                    return True
                
        else:
            return False
        
    @staticmethod
    def three_pt_approach_simple(d0, d1, d2, approach_distance) -> bool:
        ret_flag = False
        if d0 >= approach_distance:
            if d1 >= approach_distance:
                if d2 <= approach_distance:
                    ret_flag = True 
        return ret_flag

    #  heuristic: d0 and d1 upstream from sight distance (X), d2 downstream of sight distance(X)
    #  -d0-------d1----X-----d2------0
    def h_prev_and_current_before_next(self, approaching_intersection: Intersection, b_index: int) -> bool:
        h_flag = False
        p_prev = self.get_prev_gpx_point()
        p_next = self.get_next_gpx_point()

        approach_i_sd = approaching_intersection.get_sd(b_index)

        approach_i_sb_pt1 = approaching_intersection.stop_bar_d[b_index][0]
        approach_i_sb_pt2 = approaching_intersection.stop_bar_d[b_index][1]
        
        if not approaching_intersection.sb_line_available(b_index):
            """using center point of intersection"""
            d0 = p_prev.distance_to(approaching_intersection.get_location()) 
            d1 = self.distance_to(approaching_intersection.get_location())
            if p_next is not None:
                d2 = p_next.distance_to(approaching_intersection.get_location())
            else:
                d2 = 0
        else:
            """using stop bar at intersection information"""
            d0 = p_prev.distance_to(approaching_intersection.get_location_sb(b_index)) #+ approaching_intersection.center_to_sb_distance(b_index) + self.veh_gap
            d1 = self.distance_to(approaching_intersection.get_location_sb(b_index)) #+ approaching_intersection.center_to_sb_distance(b_index) + self.veh_gap
            if p_next is not None:
                d2 = p_next.distance_to(approaching_intersection.get_location_sb(b_index)) #+ approaching_intersection.center_to_sb_distance(b_index) + self.veh_gap
            else:
                d2 = 0
 
        #h_flag = self.three_pt_approach_simple(d0, d1, d2, approach_i_sd)

        if d0 >= approach_i_sd:
            if d1 >= approach_i_sd:
                if d2 <= approach_i_sd:
                    h_flag = True

        return h_flag
    
   
    def generic_so_prev_and_current_before_next(self, approaching_generic_so) -> bool:
        
        h_flag = False
        p_prev = self.get_prev_gpx_point()
        p_next = self.get_next_gpx_point()

        approach_generic_so_sd = approaching_generic_so.get_sd()

        d0 = p_prev.distance_to(approaching_generic_so.get_location())
        d1 = self.distance_to(approaching_generic_so.get_location())
        if p_next is not None:
            d2 = p_next.distance_to(approaching_generic_so.get_location())
        else:
            d2 = 0
        h_flag = self.three_pt_approach(d0, d1, d2, approach_generic_so_sd)
        return h_flag


    #  heuristic: d2 less than d1
    #  -d1---X----d2------0
    def h_next_less_than_current(self, approaching_intersection: Intersection, b_index: int) -> bool:
        h_flag = False
        p_next = self.get_next_gpx_point()
        approach_i_sd = approaching_intersection.get_sd(b_index)
        approach_i_sb_pt1 = approaching_intersection.stop_bar_d[b_index][0]
        approach_i_sb_pt2 = approaching_intersection.stop_bar_d[b_index][1]

        if not approaching_intersection.sb_line_available(b_index):
            d1 = abs(self.distance_to(approaching_intersection.get_location()))
            if p_next is not None:
                d2 = abs(p_next.distance_to(approaching_intersection.get_location()))
            else:
                d2 = 0
        else:
            d1 = abs(self.distance_to(approaching_intersection.get_location_sb(b_index))) #+ approaching_intersection.center_to_sb_distance(b_index) + self.veh_gap
            if p_next is not None:
                d2 = abs(p_next.distance_to(approaching_intersection.get_location_sb(b_index)))# + approaching_intersection.center_to_sb_distance(b_index) + self.veh_gap
            else:
                d2 = 0

        if d2 <= d1:
            h_flag = True

        return h_flag
    
    def simple_intersection_approach(self, approaching_intersection: Intersection, b_index: int) -> bool:
        ret_flag = False
        p_prev = self.get_prev_gpx_point()
        approach_generic_so_sd = approaching_intersection.get_sd(b_index)

        d0 = p_prev.distance_to(approaching_intersection.get_location())
        d1 = self.distance_to(approaching_intersection.get_location())

        if d0 >= approach_generic_so_sd >= d1:
                ret_flag = True

        return ret_flag

    def generic_so_next_less_than_current(self, approaching_generic_so) -> bool:
        h_flag = False
        p_next = self.get_next_gpx_point()
        approach_generic_so_sd = approaching_generic_so.get_sd()

        d1 = abs(self.distance_to(approaching_generic_so.get_location()))
        if p_next is not None:
            d2 = abs(p_next.distance_to(approaching_generic_so.get_location()))
        else:
            d2 = 0

        if d2 <= d1:
            h_flag = True

        return h_flag
    
    def generic_so_single_filter(self, approaching_generic_so):
        capture_flag = False
        p_prev = self.get_prev_gpx_point()
        p_next = self.get_next_gpx_point()
        gso_sd = approaching_generic_so.get_sd()

        d1 = self.distance_to(approaching_generic_so.get_location()) - gso_sd
        d2 = p_next.distance_to(approaching_generic_so.get_location()) + gso_sd
        d_to_next_pt = self.get_dist_to_next_point()

        if d1 < d_to_next_pt:
            capture_flag = True
        return capture_flag, abs(d1)
    

    
            

    # TODO: consider developing heuristic based on --d0----d1----X---0  without a next_d available