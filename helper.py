from ultralytics import YOLO
import os
import re
import csv
import haversine as hs
from PIL import Image
from pyproj import Geod


def detect_and_store(src, modelName, locationStr = None):
    model = YOLO(modelName)
    results = model.predict(source=src, conf=0.25)
    result = results[0]
    highConfSigns = []
    signTypes = []
    for box in result.boxes:
        signName = result.names[int(box.cls)]
        #path = os.path.join(os.getcwd(), f"images/{signName}_Low_Confidence")
        if box.conf.item() >= 0.8:
            #track all signs
            highConfSigns.append([signName, box.conf.item(), box.xyxy.tolist()[0]])
            #save one image per sign type
            if signName not in signTypes:
                signTypes.append(signName)
                path = os.path.join(os.getcwd(), f"images/{signName}_High_Confidence")
                os.makedirs(path, exist_ok = True)
                outputPath = f"{path}/{re.findall(r'streetview_frame_\d+_heading_\d+', src)[0]}.jpg"
                result.save(outputPath)

        #result.save(outputPath)
    return highConfSigns
            
        
def addToTable(filename, signName, location, url, heading, confidence):
    item = {
    'SignName' : signName,
    'ImageURL' : url,
    'Location' : location,
    'Heading': heading,
    'Confidence' : confidence
    }
    fields = ['SignName', 'ImageURL', 'Location', 'Heading', 'Confidence']
    if(os.path.exists(filename)):
        with open(file = filename, mode = "a", newline='') as f:
            writer = csv.DictWriter(f, fieldnames = fields)
            writer.writerow(item)

    else:
        with open(file = filename, mode = "x", newline='') as f:
            writer = csv.DictWriter(f, fieldnames = fields)
            writer.writeheader()
            writer.writerow(item)


def addToGISFormatTable(filename, signName, lat, long, heading):
    item = {
        'x': long,
        'y': lat,
        'z': 0.0,
        'Sign_Type': signName,
        'Sign_Suprt': "n/a",
        'Suprt_Locat': "n/a",
        'Mnt_Height': "n/a",
        'MUTCD': "n/a",
        'Stock_No': "n/a",
        'Sign_Size': "n/a",
        'Sign_Text': "n/a",
        'P_Street': "n/a",
        'Crs_Street': "n/a",
        'EoB': "n/a",
        'Side_Str': "n/a",
        'Traf_face': "n/a",
        'Dir_X_Str': "n/a",
        'Sign_Dir': "n/a",
        'Condition': "n/a",
        'Post_Type': "n/a",
        'Mnt_Surf': "n/a",
        'Cncil_Dstr': "n/a",
        
    }
    fields = item.keys()
    if(os.path.exists(filename)):
        with open(file = filename, mode = "a", newline='') as f:
            writer = csv.DictWriter(f, fieldnames = fields)
            writer.writerow(item)

    else:
        with open(file = filename, mode = "x", newline='') as f:
            writer = csv.DictWriter(f, fieldnames = fields)
            writer.writeheader()
            writer.writerow(item)


def trim_points_by_distance(points, interval):
    trimmedPoints = []
    currDist = 0
    trimmedPoints.append(points[0])
    for i in range(1, len(points)-1):
        lat1, long1 = trimmedPoints[len(trimmedPoints)-1]
        lat2, long2 = points[i]



        dist = hs.haversine((lat1, long1), (lat2, long2), hs.Unit.METERS, normalize = True)
        if(dist > interval):
            trimmedPoints.append(points[i])

    return trimmedPoints


def get_detection_depth_and_heading(model, src, boxCoords, heading, fov):
    rawSrc = newSrc = src[0:len(src)-3] + "_raw_depth.jpg" 
    boxCoords = [int(i) for i in boxCoords]
    with Image.open(src) as image:
        depth = model(image)['predicted_depth']
        depthImg = model(image)['depth']
        depthImg.save(rawSrc)
    #get depth
    sum = 0
    x1, y1, x2, y2 = boxCoords
    for row in depth[y1:y2]:
        for pixel in row[x1:x2]:
            sum += pixel
    avg_depth = sum/((x2-x1)*(y2-y1))
    #update heading
    centerX = depth.size(1)/2
    boxX = (x1+x2)/2
    percentOffset = ((centerX - boxX)*-1)/depth.size(1)
    adjustedFov = fov + (fov*percentOffset)
    print(adjustedFov)
    return (avg_depth.item(), adjustedFov)


def adjustCoords(lat, lon, bearing, depth):
    geod = Geod(ellps="clrk66")
    lon, lat, heading = geod.fwd(lons=lon, lats=lat, az=bearing, dist=depth, return_back_azimuth=False)
    return lat, lon
