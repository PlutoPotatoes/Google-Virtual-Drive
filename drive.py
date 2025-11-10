import polyline
import requests
import os
import csv
from google.maps import routing_v2
import json
from transformers import pipeline
from helper import *
from paddleocr import PaddleOCR

ocrSigns = ["Tow Away Signs Letters"]


def csv_drive(filename, API_KEY, fov = 90, pitchAngle=0, datafile = None):
    data_list = []
    if(datafile != None):
        os.makedirs(f'tables', exist_ok = True)


    with open(filename, 'r', newline='') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            data_list.append([row[1], row[2]])
    data_list.pop(0)

    outputFolder = "images/raw"
    os.makedirs(outputFolder, exist_ok = True)
    #max image size is 640x640
    imageSize = "640x640"
    i=1

    #load Depth Anything v2 Model
    depthModel = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")

    #load paddleOCR model
    ocrModel = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False)
    
    #get pictures from the longitude latitude points using streetview api and save them
    for (log, lat) in data_list:
        locationStr = f"{lat},{log}"
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={locationStr}&key={API_KEY}"
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            details = json.loads(response.content)
            locationStr = f"{details["location"]["lat"]},{details["location"]["lng"]}"
        except Exception as e:
            print(e)        

        for headingMult in range(360//fov):
            url = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch={pitchAngle}&key={API_KEY}&heading={fov*headingMult}&scale=2&radius=10"
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                imagePath = os.path.join(outputFolder, f"streetview_frame_{i}_heading_{fov*headingMult}.jpg")
                with open(imagePath, 'wb') as outfile:
                    outfile.write(response.content)
                for model in os.listdir(os.path.join(os.getcwd(), "models")):
                    found = detect_and_store(f"images/raw/streetview_frame_{i}_heading_{fov*headingMult}.jpg", f"models/{model}", locationStr)
                    if(datafile != None):   
                        for sign, conf, shape in found:
                            strippedurl = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch={pitchAngle}&key=#####&heading={fov*headingMult}&scale=2&radius=10&source=outdoor"
                            depth, newHeading = get_detection_depth_and_heading(depthModel, imagePath, shape, fov*headingMult, fov)
                            lat, lon = adjustCoords(lat, log, newHeading, depth)
                            if sign in ocrSigns:
                                sign = ocr(shape, sign, f"images/raw/streetview_frame_{i}_heading_{fov*headingMult}.jpg",
                                        f"images/temp/cropped/crop_frame_{i}_heading_{fov*headingMult}_sign_{sign}.jpg", ocrModel)
                            addToGISFormatTable(datafile, sign, lat, lon, newHeading)
            except Exception as e:
                print(e)
        i+=1




def drive_route(origin, destination, API_KEY, minStep = 20, fov = 90, pitchAngle = 10, datafile = None):

    if(datafile != None):
        os.makedirs(f'tables', exist_ok = True)

    #find directions and convert to polyline and then longitude, latitude pairs
    client = routing_v2.RoutesClient(
        client_options={"api_key" : API_KEY},

    )
    route_origin = routing_v2.Waypoint(address = origin)
    route_destination = routing_v2.Waypoint(address = destination)
    request = routing_v2.ComputeRoutesRequest(
        origin = route_origin, 
        destination = route_destination,    
        route_modifiers = routing_v2.RouteModifiers(avoid_highways = True)
        )
    
    
    route = client.compute_routes(request= request, metadata=[("x-goog-fieldmask", "routes.polyline.encodedPolyline")])
    route = route.routes[0]
    route_polyline = route.polyline.encoded_polyline
    route_points = polyline.decode(route_polyline)
    #prepare images folder

    outputFolder = "images/raw"
    croppedImageFolder = "images/temp/cropped"
    os.makedirs(outputFolder, exist_ok = True)
    os.makedirs(croppedImageFolder, exist_ok=True)

    #max image size is 640x640
    imageSize = "640x640"
    i=1

    #trim any points that are too close to each other
    route_points = trim_points_by_distance(route_points, minStep)

    #load Depth Anything v2 Model
    depthModel = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")

    #load paddleOCR model
    ocrModel = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False)


    #get pictures from the longitude latitude points using streetview api and save them
    for (log, lat) in route_points:
        locationStr = f"{log},{lat}"
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={locationStr}&key={API_KEY}"
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            details = json.loads(response.content)
            locationStr = f"{details["location"]["lat"]},{details["location"]["lng"]}"
            log = details["location"]["lng"]
            lat = details["location"]["lat"]
        except Exception as e:
            print(e)       

        for headingMult in range(360//fov):
            url = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch={pitchAngle}&key={API_KEY}&heading={fov*headingMult}&scale=2&radius=10"
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                imagePath = os.path.join(outputFolder, f"streetview_frame_{i}_heading_{fov*headingMult}.jpg")
                with open(imagePath, 'wb') as outfile:
                    outfile.write(response.content)

                #Sign Detection starts here
                for model in os.listdir(os.path.join(os.getcwd(), "models")):
                    found = detect_and_store(f"images/raw/streetview_frame_{i}_heading_{fov*headingMult}.jpg", f"models/{model}")
                    if(datafile != None):   
                        for sign, conf, shape in found:
                            strippedurl = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch={pitchAngle}&key=#####&heading={fov*headingMult}&scale=2&radius=10"
                            depth, newHeading = get_detection_depth_and_heading(depthModel, imagePath, shape, fov*headingMult, fov)
                            lat, lon = adjustCoords(lat, log, newHeading, depth)
                            if sign in ocrSigns:
                                sign = ocr(shape, sign, f"images/raw/streetview_frame_{i}_heading_{fov*headingMult}.jpg",
                                        f"images/temp/cropped/crop_frame_{i}_heading_{fov*headingMult}_sign_{sign}.jpg", ocrModel)
                            addToGISFormatTable(datafile, sign, lat, lon, newHeading)
            except Exception as e:
                print(e)
        i+=1





def drive_gopro(input_mp4, interval, datafile):
    #prepare images folder

    outputFolder = "images/raw"
    croppedImageFolder = "images/temp/cropped"
    os.makedirs(outputFolder, exist_ok = True)
    os.makedirs(croppedImageFolder, exist_ok=True)
    #load Depth Anything v2 Model
    depthModel = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")

    #load paddleOCR model
    ocrModel = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False)

    frames = GoProFrames(input_mp4, outputFolder, interval)
    #FIXME Find a way to get FOV and heading from the gopro data
    heading = 0
    fov = 90
    for (framesrc, lat, log) in frames:
        locationStr = f"{log},{lat}"     
        #Sign Detection starts here, may need to fix pathing name
        for model in os.listdir(os.path.join(os.getcwd(), "models")):
            found = detect_and_store(framesrc, f"models/{model}")
            if(datafile != None):   
                for sign, conf, shape in found:
                    depth, newHeading = get_detection_depth_and_heading(depthModel, framesrc, shape, heading, fov)
                    lat, lon = adjustCoords(lat, log, newHeading, depth)
                    if sign in ocrSigns:
                        sign = ocr(shape, sign, framesrc,
                                f"images/temp/cropped/crop_{framesrc}", ocrModel)
                    addToGISFormatTable(datafile, sign, lat, lon, newHeading)
