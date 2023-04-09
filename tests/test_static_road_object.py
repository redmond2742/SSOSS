import unittest
from ssoss.static_road_object import *
import geopy, geopy.distance


class TestGetIDNumMethod(unittest.TestCase):
    speed_sightD_tuple = {
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
    test_sro = StaticRoadObject(100, "street_name", "test_object", \
                                geopy.Point(37.79205307308094, -122.40918793416158), \
                                speed_sightD_tuple)
    sro_id_result = test_sro.get_id_num()

    def test_get_id_num_type(self):
        self.assertIsInstance(self.sro_id_result, int)

    def test_get_id_num_result(self):
        expected_value = 100
        self.assertEqual(self.sro_id_result, expected_value)


class TestDistanceToSB(unittest.TestCase):
    intersection_name = tuple(("California", "Powell"))
    intersection_ctr_pt = geopy.Point(37.79205307308094, -122.40918793416158)
    #intersection_ctr_pt = geopy.Point(37.792985856555575, -122.40938192768054)
    intersection_spd_tuple = (25, 25, 25, 25)
    intersection_bearing = tuple((346.33, 90.09, 174.52, 271.11))
    intersection_stop_bar_nb = (geopy.Point(37.791939238323664, -122.40915035636318),
                                geopy.Point(37.79194559709975, -122.4091101232288))
    intersection_stop_bar_eb = (geopy.Point(37.79201448380549, -122.40931531221416),
                                geopy.Point(37.79195725485446, -122.40930324227385))
    intersection_stop_bar_sb = (geopy.Point("",""),geopy.Point("",""))

    intersection_stop_bar_wb = (geopy.Point(37.792081947979, -122.40908296974182),
                                geopy.Point(37.792137440921714, -122.40909664953729))

    test_intersection = Intersection(100,
                                     intersection_name,
                                     intersection_ctr_pt,
                                     intersection_spd_tuple,
                                     intersection_bearing,
                                     intersection_stop_bar_nb,
                                     intersection_stop_bar_eb,
                                     intersection_stop_bar_sb,
                                     intersection_stop_bar_wb)

    test_nb_approach_point = geopy.Point(37.791640829945806, -122.4090598924283)
    test_eb_approach_point = geopy.Point(37.79191109041387, -122.41001431676943)
    test_sb_approach_point = geopy.Point(37.79329947700734, -122.40947874960277)
    test_wb_approach_point = geopy.Point(37.79221743892232, -122.40836821431033)

    nb_result = test_intersection.distance_to_sb(test_nb_approach_point, 0)
    eb_result = test_intersection.distance_to_sb(test_eb_approach_point, 1)
    sb_result = test_intersection.distance_to_sb(test_sb_approach_point, 2)
    wb_result = test_intersection.distance_to_sb(test_wb_approach_point, 3)

    def test_nb_distance_to_sb(self):
        #  exact distance is 112 ft
        self.assertGreater(self.nb_result, 108)
        self.assertLess(self.nb_result, 117)

    def test_eb_distance_to_sb(self):
        #  exact distance is 205.6
        self.assertGreater(self.eb_result, 200)
        self.assertLess(self.eb_result, 211)

    def test_sb_distance_to_sb(self):
        #  exact distance is 458 ft
        self.assertGreater(self.sb_result, 453)
        self.assertLess(self.sb_result, 463)

    def test_wb_distance_to_sb(self):
        #  exact distance is 210 ft
        self.assertGreater(self.wb_result, 205)
        self.assertLess(self.wb_result, 215)


if __name__ == '__main__':
    unittest.main()
