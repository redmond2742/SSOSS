# !/usr/bin/env python
# coding: utf-8

import csv, math
from datetime import datetime, timezone
from pathlib import Path

import geopy
from geopy.distance import geodesic, Distance

import gpxpy
import gpxpy.gpx

import pandas as pd
import lxml
from lxml import etree
from tqdm import tqdm

from ssoss.static_road_object import Intersection, GenericStaticObject
from ssoss.motion_road_object import GPXPoint


class ProcessRoadObjects:

    def __init__(self,
                 gpx_filestring: str = "",
                 #signals_filestring: str = "",
                 generic_static_object_filestring: str = ""
                 ):
        """ Class to process Road Object files. Using January 1st 1970 as time epoc

        :gpx_filepath: as string, full directory and filename of gpx file
        :signals_filepath: as string, full directory and filename of sign or signal CSV file
        generic_static_object_filestring: as string, full directory and filename of generic SO CSV file
        """

        self.intersection_load = None
        self.intersection_listDF = None

        self.generic_so_load = None  #id, generic_SO object list
        self.generic_so_listDF = None # data frame of generic_SO object list

        self.date_format = "%m-%d-%Y--%H-%M-%S.%f-%Z"
        self.pretty_datetime_format = "%y-%m-%d %H:%M:%S"
        self.in_gpx_dir_path = Path(gpx_filestring).parent
        self.in_dir_path = self.in_gpx_dir_path
        self.out_dir_path = Path(self.in_dir_path, "/out/") #  self.in_dir_path / "out/"
        self.out_dir_path.parent.mkdir(exist_ok=True, parents=True)

        # init variables
        #if signals_filestring:
        #    self.intersection_filename = Path(signals_filestring)
        if generic_static_object_filestring:
            self.generic_so_filename = Path(generic_static_object_filestring)
        self.gpx_filename = Path(gpx_filestring).stem
        self.pickle_file = ''
        self.gpx_file = ''
        self.csv_file = None
        self.gpxDF = ''
        self.gpx_listDF = None
        self.gDF_pickle_file = None

        self.sum_time_gap = 0.0
        self.sum_total_points = 0.0

        self.intersection_approaches = 0
        self.generic_so_approaches = 0

        # scafold directory structure if not present
        gpx_video_dir = self.in_gpx_dir_path
        p = Path(str(gpx_video_dir))

        self.static_object_type = ""

        """
        if signals_filestring:
            all_intersections_df = self.load_intersection_csv(self.intersection_filename)
        """
        if generic_static_object_filestring:
            # if filestring file has 7 rows, load_generic_so_csv, else load_intersection_csv
            with open(self.generic_so_filename, 'r') as f:
                reader = csv.reader(f)
                so_file_columns = len(next(reader))
            if so_file_columns == 7:
                self.static_object_type = "generic static object"
                all_generic_so_df = self.load_generic_so_csv(self.generic_so_filename)
            elif so_file_columns == 13 or so_file_columns == 29:
                self.static_object_type = "intersection"
                all_intersections_df = self.load_intersection_csv(self.generic_so_filename)
            else:
                raise ValueError("generic static object .csv file must have 7, 13 or 29 columns. Check documentation.")
        if self.gpx_filename:
            gpx_df = self.load_gpx_to_obj_df(self.gpx_filename, use_pickle=False)


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
    
    def get_generic_so_object_by_id(self, id):
        return self.generic_so_listDF.iloc[id-2, 1]
    
    def get_static_object_type(self):
        return self.static_object_type

    def generic_so_description(self, sro_id, distance, ts, desc_type="filename"):
        """
        create descriptive labels for image filenames and labels at bottom of image
        creates descriptive labels for generic static objects
        
        """
        generic_so_id = sro_id
        generic_so_obj = self.get_generic_so_object_by_id(sro_id)
        generic_so_name = generic_so_obj.get_name()
        generic_so_sd = int(generic_so_obj.get_sd())
        generic_so_dist = distance
        ts_utc = round(ts, 3)
        dt_temp = datetime.fromtimestamp(ts, tz=None)
        date_time = dt_temp.strftime("%a, %b %e %Y at %I:%M %p")  # Note: using %-[char] gives error for windowsOS

        if desc_type == "filename":
            filename_desc = f'{generic_so_id}.{generic_so_sd}-{generic_so_name}-{generic_so_obj.get_description()}-{ts_utc}'
            return filename_desc
        elif desc_type == "label":
            label = f'{generic_so_obj.get_bearing_str()} {generic_so_name} (#{sro_id}) {generic_so_obj.get_description()} at ~{generic_so_sd} ft on {date_time}'
            return label


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
        date_time = dt_temp.strftime("%a, %b %e %Y at %I:%M %p")  # %-[char] gives error for windowsOS

        # Note-to-self: don't use "/" when building filename string
        if desc_type == "filename":
            filename_desc = f'{i_id}.{i_bearing}-{i_name}-{i_sd}-{ts_utc}'
            return filename_desc
        elif desc_type == "label":
            label = f'{i_compass_bearing} approach of {i_name_one} and {i_name_two} (#{sro_id}) at ~{i_sd} ft on {date_time}'
            return label

    def load_generic_so_csv(self, generic_so_filename: str) -> pd.DataFrame:
        """ Loads CSV file into Generic Static Object Class DataFrame
        :param generic_so_filename: name of CSV file for loading (leave off .csv)
            Format: #,Street Name,latitude,longitude,direction,object type, distance
        :return: dataframe of generic static objects in each row
        """

        csv_generic_so_file = Path(self.in_dir_path, generic_so_filename)
        self.generic_so_load = {"id": [], "generic_so_obj": []}

        with open(csv_generic_so_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            next(csv_reader, None)  # skip the header
            line_count = 0
            for row in csv_reader:
                try:
                    self.generic_so_load["id"].append(int(row[0]))
                    self.generic_so_load["generic_so_obj"].append(GenericStaticObject(
                        id_num = int(row[0]),
                        street_name = str(row[1]),
                        pt = geopy.Point(float(row[2]),float(row[3])),
                        bearing = row[4],
                        description = str(row[5]),
                        distance_ft = float(row[6])            
                    ))
                except:
                    print("Check intersection input file formatting.\n"
                          "Input should be:\n"
                          "#,Street Name,Latitude, Longitude, Bearing (NB,EB,SB,WB), Description, Distance (in feet)\n"
                          )
                line_count += 1
            self.generic_so_listDF = pd.DataFrame(self.generic_so_load)
            print(
                f"Processed {line_count} lines of CSV file")
            print(
                f"for a total of {len(self.generic_so_listDF.index)} Generic Static Object(s)")
            

    def load_intersection_csv(self, intersection_filename: str) -> pd.DataFrame:
        """ Loads CSV file into Intersection Class DataFrame

        :param intersection_filename: name of CSV file for loading (leave off .csv)
            CSV Format: #,name1(N/S),name2(E/W),latitude,longitude,spd_N,spd_E,spd_S,spd_W,bearing_N,bearing_E,bearing_S,bearing_W,
        :return: dataframe of intersections objects in each row
        """

        csv_intersection_file = Path(self.in_dir_path, intersection_filename)
        self.intersection_load = {"id": [], "intersection_obj": []}
        with open(csv_intersection_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            next(csv_reader, None)  # skip the header
            line_count = 0
            count_sb_i = 0
            for row in csv_reader:
                columns_in_row = len(row)
                if columns_in_row == 13:
                    self.intersection_load["id"].append(int(row[0]))
                    self.intersection_load["intersection_obj"].append(Intersection(
                        id_num = int(row[0]),
                        # name1(N/S), name2(E/W)
                        name = tuple((str(row[1]),str(row[2]))),
                        ctr_pnt = geopy.Point(float(row[3]),float(row[4])),
                        # spd_N, spd_E, spd_S, spd_W
                        spd = tuple((int(row[5]), int(row[6]), int(row[7]),int(row[8]))),
                        # bearing_N, bearing_E, bearing_S, bearing_W
                        bearing = tuple((float(row[9]), float(row[10]), float(row[11]),
                            float(row[12])))
                    ))
                elif columns_in_row == 29:
                    nb_sb_pts = eb_sb_pts = sb_sb_pts = wb_sb_pts = False
                    if (row[13] and row[14] and
                        row[15] and row[16]) != "": nb_sb_pts = True
                    if (row[17] and row[18] and
                        row[19] and row[20]) != "": eb_sb_pts = True
                    if (row[21] and row[22] and
                        row[23] and row[24]) != "": sb_sb_pts = True
                    if (row[25] and row[26] and
                        row[27] and row[28]) != "": wb_sb_pts = True

                    self.intersection_load["id"].append(int(row[0]))
                    temp_i = Intersection(
                        id_num = int(row[0]),
                        # name1(N/S), name2(E/W)
                        name = tuple((str(row[1]),str(row[2]))),
                        ctr_pnt = geopy.Point(float(row[3]),float(row[4])),
                        # spd_N, spd_E, spd_S, spd_W
                        spd = tuple((int(row[5]), int(row[6]), int(row[7]),
                            int(row[8]))),
                        # bearing_N, bearing_E, bearing_S, bearing_W
                        bearing = tuple((float(row[9]), float(row[10]), float(row[11]),
                            float(row[12]))),
                        # Additional info for stop bar to improve accuracy:
                        # NB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        stop_bar_nb = tuple((geopy.Point(row[13], row[14]),
                            geopy.Point(row[15], row[16]))),
                        # EB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        stop_bar_eb = tuple((geopy.Point(row[17], row[18]),
                            geopy.Point(row[19], row[20]))),
                        # SB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        stop_bar_sb = tuple((geopy.Point(row[21], row[22]),
                            geopy.Point(row[23], row[24]))),
                        # WB Stop bar. center line Point(lat, lon), shoulder Point(lat, lon)
                        stop_bar_wb = tuple((geopy.Point(row[25], row[26]),
                            geopy.Point(row[27], row[28])))
                    )
                    temp_i.set_sb_pts_bools((nb_sb_pts,eb_sb_pts,sb_sb_pts,wb_sb_pts))
                    self.intersection_load["intersection_obj"].append(temp_i)
                    
                    if temp_i.all_sb_line_available(): count_sb_i += 1

                    
                else:
                    print("Check intersection input file formatting.\n"
                          "Input should be:\n"
                          "#,Street Name1, Steet Name2, Latitude, Longitude, Speed Limit_NB, SL_EB, SL_SB, SL_WB, Bearing_NB, B_EB, B_SB, B_WB\n"
                          "Optional additional input for stop bar lines after bearing\n"
                          "NB_Left_StopBar_Latitude, NB_Left_StopBarLongitude, NB_Right_StopBar_Latitude, NB_Left_StopBar_Longitude\n"
                          "Same for EB Stop Bar, SB Stop Bar, and WB Stop Bar\n"
                          )
                line_count += 1
            self.intersection_listDF = pd.DataFrame(self.intersection_load)
            print(
                f"Processed {line_count} lines of CSV file for a total of {len(self.intersection_listDF.index)} intersections, \n \
                and of those {count_sb_i} with stop bar information."
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
        # TODO: set timezone with lat, lon coordinates:
        #  (https://stackoverflow.com/questions/15742045/getting-time-zone-from-lat-long-coordinates)

        gpx = gpxpy.parse(gpx_file_ref, version=self.gpx_ver)
        pt_count = 0
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if self.gpx_ver == "1.1":
                        extra_data = {}
                        if len(point.extensions) > 0:
                            extension_data = {
                                lxml.etree.QName(child).localname: float(child.text)
                                for child in point.extensions[0]
                            }
                            for k, v in extension_data.items():
                                extra_data[k] = v
                            if point.speed is not None:
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
                    )
                    pt_count += 1

        self.gpx_listDF = pd.DataFrame(gpx_load)
        #self.gpx_listDF.to_pickle(self.pickle_file)
        #self.gpx_listDF.to_csv(self.csv_file)
        print(
            f"Processing {pt_count} points of GPX file."
        )
        if self.intersection_listDF is not None:
            self.update_gpx_points(so_type = "intersection")
        if self.generic_so_listDF is not None:
            self.update_gpx_points(so_type = "generic_so")
        self.gpx_summary()
        return self.gpx_listDF

    def update_gpx_points(self, so_type):
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

        # display progress bar for calculating time-consuming/unoptimized backflow function
        for i in tqdm(range(len(gpx_df.index))):
            if so_type == "intersection":
                gpx_df.iloc[i, 0].backflow(self.intersection_listDF, "intersection")
            elif so_type == "generic_so":
                gpx_df.iloc[i, 0].backflow(self.generic_so_listDF, "generic_so")

    def get_start_timestamp(self):
        return self.gpx_listDF.iloc[0, 0].get_timestamp()

    def get_end_timestamp(self):
        last_index = self.gpx_listDF.last_valid_index()
        return self.gpx_listDF.iloc[last_index, 0].get_timestamp()
    
    def generic_so_checks(self):
        """
        perform generic distance check on static road object
        """
        gpx_df = self.gpx_listDF
        all_generic_so = self.generic_so_listDF
        generic_so_desc = []
        generic_so_ts = []
        generic_so_error = []
        bearing_buffer_angle = 50
        time_buffer = 3

        for point in range(len(gpx_df.index)):
            generic_so_info = gpx_df.iloc[point, 0].get_generic_so_approach_list()
          
            if generic_so_info:
                p = gpx_df.iloc[point, 0]
                generic_so_id, dist, approaching_bool = zip(*generic_so_info)
                for item in range(len(list(generic_so_id))):
                    sro_id = int(list(generic_so_id)[item])
                    d_current = list(dist)[item]

                    approach_generic_so = all_generic_so.iloc[sro_id-1, 1]  # shift by 1 for generic_so dataframe (starting at 0, not 1)
                    approach_generic_so_sight_distance = approach_generic_so.get_sd()
      
                    if p.calc_bearing_diff(approach_generic_so.get_bearing()) < bearing_buffer_angle:
                        print(
                            f"Generic Object #{sro_id} at {approach_generic_so_sight_distance} ft at {p.get_timestamp()}"
                        )
                        prev_current_b4_next = p.generic_so_prev_and_current_before_next(approach_generic_so)
                        next_less_than_current = p.generic_so_next_less_than_current(approach_generic_so)  
                        neg_dist = p.distance_to(approach_generic_so.get_location()) - approach_generic_so_sight_distance
                        #if prev_current_b4_next and next_less_than_current:
                        filtered_sightings = p.generic_so_single_filter(approach_generic_so)
                
                        if filtered_sightings[0] and (neg_dist < 0):
                            t_acc = p.t_to_generic_so_acc(approach_generic_so)
                            print(
                                f"Generic Object #{sro_id} at {approach_generic_so_sight_distance} ft acc shift by {t_acc} with error {filtered_sightings[1]} ft"
                            )
                
                            t_shift_acc = p.get_timestamp() + t_acc
                            if approach_generic_so.print_detail_info() in generic_so_desc:
                                index_item = generic_so_desc.index(approach_generic_so.print_detail_info())
                                if t_shift_acc-time_buffer < generic_so_ts[index_item] < t_shift_acc + time_buffer:
                                    if filtered_sightings[1] < generic_so_error[index_item]:
                                        #todo: make remove function
                                        del generic_so_desc[index_item]
                                        del generic_so_ts[index_item]
                                        del generic_so_error[index_item]
                                        #todo: make append function
                                        generic_so_desc.append(approach_generic_so.print_detail_info())
                                        generic_so_ts.append(t_shift_acc)
                                        generic_so_error.append(filtered_sightings[1])
                            else:
                                generic_so_desc.append(approach_generic_so.print_detail_info())
                                #generic_so_sights.append(self.generic_so_description(sro_id, approach_generic_so_sight_distance, t_shift_acc))
                                generic_so_ts.append(t_shift_acc)
                                generic_so_error.append(filtered_sightings[1])
        
     
        updated_desc = self.include_timestamp_to_description(generic_so_desc, generic_so_ts)
        z = zip(updated_desc, generic_so_ts)  # create tuples with generic Static Object descriptions,timestamps and errors
        id_ts_error = list(z)  # convert zip to list
        time_sort = sorted(id_ts_error, key=lambda x: x[1])  # sort the list by timestamps
        #id_sort = sorted(id_ts_error, key=lambda x: x[0])  # sort the list by id
        #error_sort = sorted(id_ts_error, key=lambda x: x[2])  # sort the list by errors
       
        self.generic_so_approaches = len(time_sort)
        return time_sort
    

    @staticmethod
    def include_timestamp_to_description(desc, ts):
        """ 
        add timestamp to description in one string
        """
        for i in range(len(desc)):
            desc[i] = desc[i] + "-" + str(round(ts[i],3))
        return desc

    def intersection_checks(self):
        """
        perform intersection sight distance checks.
        find timestamp of intersection approach sight distance locations
        check each GPX point
        """
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

                    approach_intersection = all_intersections.iloc[sro_id-1, 1]  
                    approach_intersection_sight_distance = approach_intersection.get_sd(b_index)

                    prev_current_b4_next = p.h_prev_and_current_before_next(approach_intersection, b_index)
                    next_less_than_current = p.h_next_less_than_current(approach_intersection, b_index)
                    simple_int_approach = p.simple_intersection_approach(approach_intersection, b_index)
       
                    if (prev_current_b4_next and next_less_than_current):
                    #if simple_int_approach:
                        t_acc = p.t_to_approach_acc(approach_intersection, b_index)
                        print(
                            f"Signal #{sro_id}.{b_index} at {approach_intersection_sight_distance} ft acc shift by {t_acc}"
                        )

                        t_shift_acc = p.get_timestamp() + t_acc
                        intersection_sd.append(self.intersection_frame_description(sro_id, b_index, d_current, t_shift_acc))
                        intersection_ts.append(t_shift_acc)

        z = zip(intersection_sd, intersection_ts)  # create tuples with intersection descriptions and timestamps
        id_ts = list(z)  # convert zip to list
        ret = sorted(id_ts, key=lambda x: x[1])  # sort the list by timestamps
        self.intersection_approaches = len(ret)
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
            min_remain = round(sec - hr * 3600, 2)
            min = int(min_remain/60)
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
        # {symbol * width}
        # IF self.intersection_approaches > 0
        # Total intersection approaches: {self.intersection_approaches}
        # Avg. Time per approach: {tot_sec/self.intersection_approaches}
        # Avg. feet driven per approach: {tot_distance/self.intersection_approaches}
        # difference in GPX and Video file start times and lengths of times
        # Number of images captured:
        # Number of intersections captures: X/ Total intersections (xx.x%)
        # Number of approaches captured
        # Approaches captures for duration of GPX file and Video File -> (images/time) (productivity ratio)
        # -------------------------------------------------------------------------------

        print(summary)

    @staticmethod
    def avg_speed(spd1, spd2):
        return (spd1 + spd2) / 2

    def get_speed_at_timestamp(self, ts):
        point_list = self.gpx_listDF
        last_point = len(point_list)-1
        speed = None

        #  boundary conditions
        #  first point check
        if ts < point_list.loc[0][0].get_timestamp():
            return None
        #  last point check
        if ts > point_list.loc[last_point][0].get_timestamp():
            return None

        for i in range(len(point_list)-1):
            if point_list.loc[i][0].get_timestamp() <= ts <= point_list.loc[i + 1][0].get_timestamp():
                speed = self.avg_speed(point_list.loc[i][0].get_speed(), point_list.loc[i+1][0].get_speed())
                break
        return speed





