# Safe Sightings of Signs and Signals (SSOSS)

[SSOSS Summary Video](https://www.youtube.com/watch?v=VbKtDvSXblM)

[Using SSOSS: A How To Video](https://youtu.be/R7qm3d8Ego8)

SSOSS is a software tool that automates the difficult aspects of verifying if traffic signs and signals are visible or obstructed on a roadway network. This is a 
streamlined and repeatable process to monitor signs and signals along any roadway using a simple input file (.CSV), GPS recorded data file (.GPX) and a synchronized recorded video file.


<p align="center">
  <img src="../media/ssoss_screenshot.png?raw=true" width=45% /> <br>
  <i> SSOSS as Windows EXE Program</i>
  <br>
  <img src="../media/15.3-Pine%2BTaylor%20St-270-1681584877.816.jpg?raw=true" width=90% />
  <br>
  <i> Sample Sight Distance Image</i>
</p>


## Features
* Automated data processing: The SSOSS scripts uses a combination of GPS and video data to extract images of traffic signals and/or roadway signs.
* Video Synchronization Helper Tools: Python methods are provided to export the video frames and help to synchronize the video file.
* Image Labeling and animated GIF image tools: Python functions are included to label images or create an animated GIF from multiple images 

## Requirements
- Python 3.8
- Required libraries: pandas, numpy, opencv-python, geopy, gpxpy, imageio, tqdm, lxml 

## Installation
Windows OS users can use the [Releases](https://github.com/redmond2742/ssoss/releases) to download an .exe of SSOSS for simple graphical usage. For Mac and Linux users, the command line option is described below.


To install SSOSS:

    python3 -m pip install ssoss

## Usage
To use the SSOSS program, 
1. Setup the necessary input files in A and B. 
2. Follow the data processing commands in Part C. Jupyter Notebook available as example

### A. Input Files
Data related to the static road objects (signs and traffic signals) need to be saved in a CSV file for used in processing.
The intersection CSV file has the following format (as a minimum):

| ID# | Cross Street 1 | Cross Street 2 | Center Intersection Latitude | Center Intersection Longitude | NB Approach Posted Speed (MPH) | EB Approach Posted Speed (MPH) | SB Approach Posted Speed (MPH) | WB Approach Posted Speed (MPH) | NB Bearing | EB Bearing | SB Bearing | WB Bearing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Pine St | Taylor St | 37.790682244556805 | -122.41229404545489 | 25 | 25 | 25 | 30 | 356.58 | 87.12 | 162.87 | 263.94 |

#### Optional Stop Bar Locations (OExperimental)
For more accurate sight distance images, stop bar locations can be appended to each intersection row. Below shows an example for the Northbound and Eastbound approaches.

| NB Stop Bar Left Side (Latitude) | NB Stop Bar Left Side (Longitude) | NB Stop Bar Right Side (Latitude) | NB Stop Bar Right Side (Longitude) | EB Stop Bar Left Side (Latitude) | EB Stop Bar Left Side (Longitude) | EB Stop Bar Right Side (Latitude) | EB Stop Bar Right Side (Longitude) | SB Stop Bar Left Side (Latitude) | SB Stop Bar Left Side (Longitude) | SB Stop Bar Right Side (Latitude) | SB Stop Bar Right Side (Longitude) | WB Stop Bar Left Side (Latitude) | WB Stop Bar Left Side (Longitude) | WB Stop Bar Right Side (Latitude) | WB Stop Bar Right Side (Longitude) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 37.79055490933646 | -122.41231165549507 | 37.79056709721846 | -122.41222448370476 | 37.79071792444257 | -122.41241972749047 | 37.790609293471164 | -122.41239692871453 | 37.79078277043246 | -122.41224998121827| 37.79076899286676 | -122.41237537448755 | 37.79064499466002 | -122.41213464623262 | 37.790755745205026 | -122.41215543335213 |


### B. Data Collection
Collect data simultaneously:
1. GPX recording
   a. Use GPX Version 1.0 with logging every second
2. Video Recording
   a. Record at 2 Megapixel resolution or more
   b. Record at 30 frames per second or higher

### C. Data Processing: Argparse Command Line
```Shell
(ssoss_virtual_env) python ssoss_cli.py -h
```

#### Basic Usage
```Shell
(ssoss_virtual_env) python ssoss_cli.py --static_objects signals.csv --gpx_file drive.gpx --video_file vid.mov 
                                        --sync_frame 456 --sync_timestamp 2022-10-24T14:21:54.32Z
```



#### Python Notebook

```python
    import ssoss as ss

signals_csv = "signal"  # .csv is omitted
gpx_file = "drive_1"  # .gpx is omitted

signal_project = ProcessRoadObjects(signals_csv, gpx_file)
sightings = signal_project.intersection_checks()

vid_file = "drive_1.MP4"
video = ss.ProcessVideo(vid_file)
video.sync(200, "2022-10-24T14:21:54.988Z")  # See Sync Process below
video.extract_sightings(sightings, signal_project)
```

At this point, progress bars should load while the sight images are saved to the output folder.

#### Sync GPX & Video Process
Synchronizing the GPX file and the video could be one of the largest sources of error. The ProcessVideo Class has
a helper function to perform a accurate synchronization time. The extract_frames_between method can export all the 
video frames between two time values. When looking at the GPX points, the approximate video time can be estimated 
and all the frames can be extracted. This method is:

```Shell
        (ssoss_virtual_env) python ssoss_cli.py -video_file vid.mov --frame_extract_start 4 --frame_extract_end 6
```

Check the printed logs to see the saved output location. Default is:
./out/[video filename]/frames/###.jpg
where ### is the frame number of the image.

Use the frame number and the GPX recorded time to line up the best point to synchronize the video using the Sync method.

### Sources of Error
While SSOSS does provide approximate sight distance images, their are various sources of error that should be try to be minimized. Here are the major sources of error and how they can be mitigated.


| **Error Source**      | **Approximate Error Amount** | **Comment**                                                                                                |
|-----------------------|------------------------------|------------------------------------------------------------------------------------------------------------|
| GPS                   | 9 ft +                       | Inherent with using GPS. Keep clear signal of GPS if possible                                              |
| Stop Bar              | 20 - 80 ft                   | Depends on size of intersection. Using stop bar points can eliminate this error.                           |
| Vehicle Motion        | 0 - 30 ft                    | Significant acceleration and deacceleration can cause error in finding the sight distance accuratly        |
| Video View of Roadway | 0 - 25 ft                    | Calibrating the closest visible ground spot as seen on the video can eliminate this error. Typically 20ft. |
| Video Time Sync       | 0 ft +                       | If the syncronization process is not done accuratly, this can be a huge source of error.                   |

## Documentation

### Helper Function: GIF Creator
Create a gif from multiple images around the sight distance location. This can be helpful if the lens is out of focus
at an extracted frame, or just more context before and after a sight distance is needed.

```python
        video.extract_sightings(sightings, signal_project, gen_gif=True)
```
Saves .gif file in ./out/[video filename]/gif/

### Heuristic

For Each GPX Point:
* What are the closest & approaching intersections
  * Based on compass heading of moving vehicle and input data (.csv), which approach leg is vehicle on?
    * What is the approach speed of that approach leg, and look up sight distance for that speed
      * Is the current GPX point greater than that sight distance and the next point is less than the sight distance,
        * If yes, then calculate acceleration between those two points and estimate the time the vehicle 
        traveled over the sight distance.
        * If no, go to next GPX point

From the sight distance timestamp and synchronized video file, the frame is extracted that is closest to that time.

## Contributions
Contributions are welcome to the SSOSS project! If you have an idea for a new feature or have found a bug, please open an issue or submit a pull request.

## License
The SSOSS project is licensed under the MIT License. See LICENSE for more information.