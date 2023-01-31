# !/usr/bin/env python
# coding: utf-8

import math

import geopy
import geopy.distance


class StaticRoadObject:

    def __init__(self, id_num: int, name: str, obj_type: type,
                 ctr_pt: geopy.Point, spd_sd: dict):
        """initializes values related to static road objects

        :param id_num: Identification number (int)
        :param name: name of street object is located on
        :param obj_type: type of static object, ie. sign, intersection, etc.
        :param ctr_pt: Geopy Point object of lat, lon, altitude
        :param spd_sd: speed [key] and sight distance[value] of object to be viewed (distance in ft)
        """

        self.id_num = id_num
        self.name = name
        self.obj_type = obj_type
        self.ctr_pt = ctr_pt
        self.pt = geopy.Point(ctr_pt.latitude, ctr_pt.longitude)  # removes elevation for dist calcs
        self.spd_sd = spd_sd

    def get_id_num(self) -> int:
        return int(self.id_num)

    def get_name(self) -> str:
        return self.name

    def get_location(self) -> geopy.Point:
        return self.ctr_pt

    def get_obj_type(self):
        return self.obj_type

    def get_sd(self):
        return self.spd_sd.values()[0]  # first/only distance (feet) to have clear view of static object.


# class for speed limit signs
class SpeedLimitSign(StaticRoadObject):
    pass


# class for radar signs that may need greater sight distance
class RadarSpeedFeedbackSign(StaticRoadObject):
    pass


# Generic class for stop signs, street name signs, curve warning signs, etc.
class TrafficControlSign(StaticRoadObject):
    pass


class Intersection(StaticRoadObject):
    """Extends Static Road Objects with additional variables and methods related to intersection objects
    """

    def __init__(self,
                 id_num,
                 name: tuple,
                 ctr_pnt: geopy.Point,
                 spd: tuple,
                 bearing: tuple,
                 stop_bar_nb=(0, 0),
                 stop_bar_eb=(0, 0),
                 stop_bar_sb=(0, 0),
                 stop_bar_wb=(0, 0)):
        """initialize variables of intersection class, mostly stored as tuples in (North, East, South, West) format

        :param id_num:
        :param name: tuple of the name of two streets intersecting ((N/S, E/W))
        :param ctr_pnt: center lat, lon of intersection as geopy.Point object
        :param spd: tuple of posted speed limit values for each approach ((N,E,S,W))
        :param bearing: tuple of compass bearing for each approach ((N,E,S,W))
        :param stop_bar_nb: tuple of two geopy Points (both with (lat,lon)) for NB approach stop bar*
        :param stop_bar_eb: tuple of two geopy Points (both with (lat,lon)) for EB approach stop bar*
        :param stop_bar_sb: tuple of two geopy Points (both with (lat,lon)) for SB approach stop bar*
        :param stop_bar_wb: tuple of two geopy Points (both with (lat,lon)) for WB approach stop bar*

        *Note: left point (inside lane) is [0] in tuple, right point (right turn lane) is [1] in tuple

        """

        self.stop_bar = None
        self.spd = spd
        self.ctr_pnt = ctr_pnt
        self.bearing = bearing
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
            60: 715
        }
        #  default to lowest distance if speed not found in spd_sd dict.
        self.sd = tuple((self.spd_sd.get(self.spd[0], 175),
                         self.spd_sd.get(self.spd[1], 175),
                         self.spd_sd.get(self.spd[2], 175),
                         self.spd_sd.get(self.spd[3], 175),
                         ))

        self.stop_bar_d = tuple((stop_bar_nb, stop_bar_eb,
                                 stop_bar_sb, stop_bar_wb
                                 ))

        StaticRoadObject.__init__(self, id_num, name, Intersection, ctr_pnt,
                                  self.spd_sd)

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

    def get_sb_distance(self, direction) -> float:
        """ NOT SURE WHAT THIS DOES
        get stop bar distance of intersection object based on compass direction/heading
        :param direction:
        :return: float od distance in feet from stop bar to event distance
        """
        return float(self.stop_bar_d[direction])

    def get_info(self) -> str:
        """ get id # and name of intersection object
        """
        return str(f'{self.get_id_num()}-{self.get_name()}')

    def distance_to_sb(self, dynamic_pt: geopy.Point,
                       direction: int) -> float:
        """ Calculates distance from point to stop bar if stop bar location is provided
        NOTE: If Stop bar distance not provided, defaults to  center of the intersection point

        :param dynamic_pt: geopy point object of dynamic object
        :param direction: index for heading of dynamic object
        :return: distance in feet as float from dynamic point to stop bar of approaching intersection
        """

        # length of stop bar
        a = geopy.distance.distance(self.stop_bar_d[direction][0],
                                    self.stop_bar_d[direction][1]).ft

        # if length of stop bar is zero, use center of intersection point.
        if a <= 0 or self.stop_bar is None:
            dis_to_ctr = geopy.distance.distance(self.pt, dynamic_pt).ft
            return dis_to_ctr
        else:
            # distance from dynamic point to inside lane stop bar point
            b = geopy.distance.distance(self.stop_bar[direction][0], dynamic_pt).ft
            # distance from dynamic point to outside lane stop bar point
            c = geopy.distance.distance(self.stop_bar[direction][1], dynamic_pt).ft

        # calculate perpendicular distance between stop bar and dynamic object
        if a is not None and b is not None and c is not None:
            s = (a + b + c) / 2
            dis_to_sb = 2. * math.sqrt(abs(s * (s - a) * (s - b) *
                                           (s - c))) / a
            return dis_to_sb
        else:
            return 0


def main():
    print("Initialize and Load Static Road Object File")
    print("Copy CSV file into ./in/ folder, where ./ is the current directory")


if __name__ == "__main__":
    main()
