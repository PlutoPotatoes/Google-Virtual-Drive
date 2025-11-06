import drive
import helper

with open('secrets.txt') as f:
    API_KEY = f.readline().strip('\n')

#select start and finish locations using google maps addresses 
origin = "100 Main St 10th Floor, Los Angeles, CA 90012"
destination = "4884 Eagle Rock Blvd, Los Angeles, CA 90041"

#Use Routes API
#drive.drive_route(origin, destination, API_KEY, minStep=30, fov = 90, datafile='tables/drive2.csv')

#Use CSV Coordinates
#drive.csv_drive("GrandAv.csv", API_KEY, pitchAngle=5, fov=90, datafile='tables/drive1.csv')

input_mp4   = "C:/Users/ryanm/LADOT/Google Maps Drive Test/video/GX040300.MP4"
outdir      = "C:/Users/ryanm/LADOT/Google Maps Drive Test/video"
interval    = 50      # seconds between frames
interp_gap  = 15.0     # per-side seconds for interpolation
nearest_gap = 10.0     # max seconds for nearest fallback

helper.GoProProcessing(input_mp4, outdir, interval, interp_gap, nearest_gap)