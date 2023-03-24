# Safe Sightings of Signs and Signals (SSOSS)

SSOSS is a Python package that helps you verify if traffic signs and signals are visible or obstructed. This is a 
streamlined and repeatable process to monitor signs and signals along any roadway using a simple input file (.CSV) as well as
GPS recorded data file (.GPX) and a synchronized recorded video file.

## Features
* Video Synchronization Helper Tools: Python methods are provided to export the video frames and help to synchronize the video file.
* Automated data processing: The SSOSS scripts uses a combination of GPS and video data to extract images of traffic signals and/or roadway signs.
* Image Labeling and animated GIF image tools: Python functions are included to label images or create an animated GIF from multiple images 

## Requirements
- Python 3.8
- Required libraries: pandas, numpy, opencv-python, geopy, gpxpy, imageio, tqdm, lxml 

## Installation
To install SSOSS, follow these steps:

    python3 -m pip install ssoss

## Usage
To use the SSOSS program, 
1. Setup the necessary input files in A and B. 
2. Follow the data processing commands in Part C. Jupyter Notebook available as example

### A. Input Files
Data related to the static road objects (signs and traffic signals) need to be saved in a CSV file for used in processing.
The intersection CSV file has the following format (as a minimum)

ID, Streetname 1, Streetname 2, Center_Latitude, Center_Longitude, Posted Speed (MPH) of NB Approach, Posted Speed (MPH) of EB Approach, 
Posted Speed (MPH) of SB Approach, Posted Speed (MPH) of WB Approach, NB Approach Compass Heading, EB Approach Compass Heading,
SB Approach Compass Heading, WB Approach Compass Heading

### B. Data Collection
Collect data simultaneously:
1. GPX recording
   a. Use GPX Version 1.0 with logging every second
2. Video Recording
   a. Record at 5 Megapixel resolution or more
   b. Record at 30 frames per second or higher

### C. Data Processing
See example notebooks (coming soon)
#### File Setup
Save Signal .CSV to:
./in/

Save GPX and Video files to:
./in/gpx_video/

#### Example Usage

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

At this point, progress bars should load while the images are saved to the output folder.

#### Sync GPX & Video Process
Synchronizing the GPX file and the video could be one of the largest sources of error. The ProcessVideo Class has
a helper function to perform a accurate synchronization time. The extract_frames_between method can export all the 
video frames between two time vales. When looking at the GPX points, the approximate video time can be estimated 
and all the frames can be extracted. This method is:

```python
        video.extract_frames_between(start_sec=20, end_sec=40)
```

Check the printed logs to see the saved output location. Default is:
./out/frames/[video filename]/###.jpg
where ### is the frame number of the image.

Use the frame number and the GPX recorded time to line up the best point to synchronize the video using the Sync method.
```python
         video.sync(frame = 200, timestamp="2022-10-24T16:45:54.988Z")
```

## Documentation
### Jupter Notebook Examples
coming soon
### Helper Function: GIF Creator
Create a gif from multiple images around the sight distance location. This can be helpful if the lens is out of focus
at an extracted frame, or just more context before and after a sight distance is needed.

```python
        video.extract_sightings(sightings, signal_project, gen_gif=True)
```
Saves .gif file in ./out/frames/ [video filename] /gif/

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