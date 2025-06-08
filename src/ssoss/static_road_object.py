# !/usr/bin/env python
# coding: utf-8

import math
from dataclasses import dataclass, field
from typing import Tuple, Union

import geopy
import geopy.distance
import numpy as np


@dataclass
class StaticRoadObject:
    """Base representation of a static object on the roadway."""

    id_num: int
    name: Union[str, Tuple[str, str]]
    ctr_pt: geopy.Point
    spd_sd: dict = field(default_factory=dict, kw_only=True)
    obj_type: type = field(init=False)
    pt: geopy.Point = field(init=False)

    def __post_init__(self) -> None:
        self.obj_type = type(self)
        self.pt = geopy.Point(self.ctr_pt.latitude, self.ctr_pt.longitude)

    def get_id_num(self) -> int:
        return int(self.id_num)

    def get_name(self) -> str:
        return self.name

    def get_location(self) -> geopy.Point:
        return self.ctr_pt

    def get_obj_type(self):
        return self.obj_type

    def get_sd(self):
        """Return the first sight distance value in ``spd_sd``.

        ``spd_sd`` is stored as a dictionary mapping speed to sight
        distance.  Prior to Python 3, ``dict.values()`` returned a list and
        indexing worked.  In Python 3 it returns a ``dict_values`` view which
        is not subscriptable.  Using ``next(iter(...))`` provides the first
        value without relying on list conversion.
        """

        return next(iter(self.spd_sd.values()))

@dataclass
class GenericStaticObject:
    """Generic static object such as a sign or road marking."""

    id_num: int
    street_name: str
    pt: geopy.Point
    bearing: Union[str, float]
    description: str
    distance_ft: float

    def __post_init__(self) -> None:
        self.pt = geopy.Point(self.pt.latitude, self.pt.longitude)

        compass = {"NB": 0, "EB": 90, "SB": 180, "WB": 270}
        if isinstance(self.bearing, str):
            self.bearing = compass[self.bearing]
        else:
            self.bearing = float(self.bearing)


    def get_id_num(self) -> int:
        return int(self.id_num)

    def get_name(self) -> str:
        return self.street_name

    def get_location(self) -> geopy.Point:
        return self.pt
    
    def get_description(self) -> str:
        return self.description
    
    def get_sd(self) -> float:
        return self.distance_ft
    
    def get_bearing(self) -> float:
        return self.bearing
    
    def get_bearing_str(self) -> str:
        quadrant = (self.bearing / 45.0)
        if 0 <= quadrant <= 1 or quadrant > 7:
            return "NB"
        elif 2 <= quadrant <= 3:
            return "EB"
        elif 4 <= quadrant <= 5:
            return "SB"
        elif 6 <= quadrant <= 7:
            return "WB"
        else:
            return "ERROR"
    
    def print_detail_info(self) -> str:
        return str(f'{self.get_id_num()}.{self.get_name()}-{self.get_bearing_str()}-{self.get_description()}-{self.get_sd()}')   

    def print_detail_info_with_ts(self,ts) -> str:
        return str(f'{self.get_id_num()}.{self.get_name()}-{self.get_bearing_str()}-{self.get_description()}-{self.get_sd()}-{ts}')   
        
    def print_info(self) -> str:
        """ print string id # and name of intersection object
        """
        return str(f'{self.get_id_num()}-{self.get_name()}')

# class for speed limit signs
class SpeedLimitSign(StaticRoadObject):
    pass


# class for radar signs that may need greater sight distance
class RadarSpeedFeedbackSign(StaticRoadObject):
    pass


# Generic class for stop signs, street name signs, curve warning signs, etc.
class TrafficControlSign(StaticRoadObject):
    pass


@dataclass
class Intersection(StaticRoadObject):
    """Static road object representing an intersection."""

    spd: Tuple[int, int, int, int]
    bearing: Tuple[float, float, float, float]
    stop_bar_nb: Tuple[geopy.Point, geopy.Point] = (
        geopy.Point(0, 0),
        geopy.Point(0, 0),
    )
    stop_bar_eb: Tuple[geopy.Point, geopy.Point] = (
        geopy.Point(0, 0),
        geopy.Point(0, 0),
    )
    stop_bar_sb: Tuple[geopy.Point, geopy.Point] = (
        geopy.Point(0, 0),
        geopy.Point(0, 0),
    )
    stop_bar_wb: Tuple[geopy.Point, geopy.Point] = (
        geopy.Point(0, 0),
        geopy.Point(0, 0),
    )

    stop_bar_bools: Tuple[bool, bool, bool, bool] = field(init=False)
    sd: Tuple[float, float, float, float] = field(init=False)
    stop_bar_d: Tuple[
        Tuple[geopy.Point, geopy.Point],
        Tuple[geopy.Point, geopy.Point],
        Tuple[geopy.Point, geopy.Point],
        Tuple[geopy.Point, geopy.Point],
    ] = field(init=False)

    def __post_init__(self) -> None:
        self.spd_sd = {
            -999: 0,
            20: 175,
            25: 215,
            30: 270,
            35: 325,
            40: 390,
            45: 460,
            50: 540,
            55: 625,
            60: 715,
        }

        self.sd = (
            self.spd_sd.get(self.spd[0], 175),
            self.spd_sd.get(self.spd[1], 175),
            self.spd_sd.get(self.spd[2], 175),
            self.spd_sd.get(self.spd[3], 175),
        )

        self.stop_bar_bools = (False, False, False, False)
        self.stop_bar_d = (
            self.stop_bar_nb,
            self.stop_bar_eb,
            self.stop_bar_sb,
            self.stop_bar_wb,
        )

        super().__post_init__()

    # TODO: Convert this to dictionary from input file, not hard coded values
    # @staticmethod
    # def spd_mph2sd(spd_mph) -> int:
    #     """ based on CA-MUTCD intersection sight distances based on speed
    #     """
    #     if spd_mph == 20:
    #         return 175
    #     elif spd_mph == 25:
    #         return 215
    #     elif spd_mph == 30:
    #         return 270
    #     elif spd_mph == 35:
    #         return 325
    #     elif spd_mph == 40:
    #         return 390
    #     elif spd_mph == 45:
    #         return 460
    #     elif spd_mph == 50:
    #         return 540
    #     elif spd_mph == 55:
    #         return 625
    #     elif spd_mph == 60:
    #         return 715
    #     else:
    #         return 0

    def get_name(self, index=-1) -> str:
        """ return name of intersection from ID #.
        """
        if index == -1:
            return str(self.name[0]) + "+" + str(self.name[1])
        elif index == 0 or index == 2:
            return str(self.name[0])
        elif index == 1 or index == 3:
            return self.name[1]

    def get_bearingT(self) -> tuple:
        return self.bearing

    def get_bearing(self, direction: int) -> float:
        return self.bearing[direction]

    @staticmethod
    def get_bearing_str(direction: int) -> str:
        if direction == 0:
            return "NB"
        elif direction == 1:
            return "EB"
        elif direction == 2:
            return "SB"
        elif direction == 3:
            return "WB"

    def get_sdT(self) -> tuple:
        return self.sd

    def get_sd(self, direction) -> float:
        """ get sight distance of this static object based on compass direction/heading
        """
        if direction == "min":
            return float(
                self.spd_sd[20] - self.spd_sd[20] * .5
                # allows for i+2 on GPX comparison to calculate when going 30mph (for 25mph zone)
            )
        elif direction == "max":
            return float(
                self.spd_sd[60] * 1.5  # allows for i+2 on GPX approaching algo for 60mph.
            )
        else:
            return round(float(self.sd[direction]))

    def get_info(self) -> str:
        """ get id # and name of intersection object
        """
        return str(f'{self.get_id_num()}-{self.get_name()}')
    
    def set_sb_pts_bools(self, t):
        """ set stop bar bools with a tuple
        """
        self.stop_bar_bools = t

    def sb_line_available(self, bearing_index) -> bool:
        """ check if specific approach stopbar line is available to use
        """
        return self.stop_bar_bools[bearing_index]
    
    def all_sb_line_available(self) -> bool:
        """ check if all stop bar variables are available
        """
        nb = self.stop_bar_bools[0]
        eb = self.stop_bar_bools[1]
        sb = self.stop_bar_bools[2]
        wb = self.stop_bar_bools[3]
        return (nb and eb and sb and wb)
    
    def center_to_sb_distance(self, bearing_index):
        """not used"""
        min_distance = min(
            geopy.distance.distance(self.ctr_pnt, self.stop_bar_d[bearing_index][0]).ft,
            geopy.distance.distance(self.ctr_pnt, self.stop_bar_d[bearing_index][1]).ft
        )
        return min_distance
    
    def get_location_sb(self, bearing_index) -> geopy.Point:
        shortest_index = np.argmin(
            [geopy.distance.distance(self.ctr_pnt, self.stop_bar_d[bearing_index][0]).ft,
            geopy.distance.distance(self.ctr_pnt, self.stop_bar_d[bearing_index][1]).ft]
        )
        return self.stop_bar_d[bearing_index][shortest_index]

    def distance_to_sb(self, dynamic_pt: geopy.Point,
                       direction: int) -> float:
        """ Calculates distance from point to stop bar if stop bar location is provided
        NOTE: If Stop bar distance not provided, defaults to  center of the intersection point

        :param dynamic_pt: geopy point object of dynamic object
        :param direction: index for heading of dynamic object
        :return: distance in feet as float from dynamic point to stop bar of approaching intersection
        """

        # length of stop bar
        if self.stop_bar_d[direction][0] is False or self.stop_bar_d[direction][1] is False:
            dist_to_ctr = geopy.distance.distance(self.pt, dynamic_pt).ft
            return dist_to_ctr
        else:
            a = geopy.distance.distance(self.stop_bar_d[direction][0],
                                    self.stop_bar_d[direction][1]).ft

        # if length of stop bar is zero, use center of intersection point.
            if a <= 0 or self.stop_bar_d is None:
                dist_to_ctr = geopy.distance.distance(self.pt, dynamic_pt).ft
                return dist_to_ctr
            else:
                if dynamic_pt is None:
                    pass
                else:
                    # distance from dynamic point to inside lane stop bar point
                    b = geopy.distance.distance(self.stop_bar_d[direction][0], dynamic_pt).ft
                    # distance from dynamic point to outside lane stop bar point
                    c = geopy.distance.distance(self.stop_bar_d[direction][1], dynamic_pt).ft

            # calculate perpendicular distance between stop bar and dynamic object
            if a is not None and b is not None and c is not None:
                s = (a + b + c) / 2
                dist_to_sb = 2. * math.sqrt(abs(s * (s - a) * (s - b) *
                                               (s - c))) / a
                return dist_to_sb
            else:
                return 0


def main():
    print("Initialize and Load Static Road Object File")
    print("Copy CSV file into ./in/ folder, where ./ is the current directory")


if __name__ == "__main__":
    main()
