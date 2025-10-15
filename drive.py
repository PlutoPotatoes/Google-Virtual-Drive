import googlemaps
import polyline
import requests
import os
import haversine as hs
from ultralytics import YOLO
import re
import csv
from google.maps import routing_v2
import json
import base64

 





def trim_points_by_distance(points, interval):
    trimmedPoints = []
    currDist = 0
    trimmedPoints.append(points[0])
    for i in range(1, len(points)-1):
        lat1, long1 = trimmedPoints[len(trimmedPoints)-1]
        lat2, long2 = points[i]
        print(f"{lat1} {long1}")
        print(f"{lat2} {long2}")


        dist = hs.haversine((lat1, long1), (lat2, long2), hs.Unit.METERS, normalize = True)
        print(dist)
        if(dist > interval):
            trimmedPoints.append(points[i])

    return trimmedPoints



def drive_directions(origin, destination, API_KEY, minStep = 20, pitchAngle = 0, datafile = None):
    gmaps = googlemaps.Client(API_KEY)
    #find directions and convert to polyline and then longitude, latitude pairs
    directions = ""
    try:
        directions = gmaps.directions(origin, destination, mode = "driving", avoid='highways')
    except Exception as e:
        print(f"Error fetching directions: {e}")
        exit()

    if not directions:
        print("Couldn't find directions")
        exit()

    route_polyline = directions[0]['overview_polyline']['points']
    route_points = polyline.decode(route_polyline)

    #prepare images folder

    outputFolder = "images/raw"
    os.makedirs(outputFolder, exist_ok = True)
    #max image size is 640x640
    imageSize = "640x640"
    fov = 60
    i=1

    #trim any points that are too close to each other
    route_points = trim_points_by_distance(route_points, minStep)


    #get pictures from the longitude latitude points using streetview api and save them
    for (log, lat) in enumerate(route_points):
        point = (log, lat)
        locationStr = f"{point[1][0]},{point[1][1]}"
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={locationStr}&key={API_KEY}"
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            details = json.loads(response.content)
            locationStr = f"{details["location"]["lat"]},{details["location"]["lng"]}"
        except Exception as e:
            print(e)       

        url = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch=0&key={API_KEY}&scale=2"
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            imagePath = os.path.join(outputFolder, f"streetview_frame_{i}.jpg")
            with open(imagePath, 'wb') as outfile:
                outfile.write(response.content)
            for model in os.listdir(os.path.join(os.getcwd(), "models")):
                found = detect_and_store(f"images/raw/streetview_frame_{i}.jpg", f"models/{model}")
                if(datafile != None):   
                    for sign, conf in found:
                        strippedurl = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch=0&key=####&scale=2"
                        addToTable(f'tables/{datafile}', sign, locationStr, strippedurl, conf)    
        except Exception as e:
            print(e)
        i+=1


def detect_and_store(src, modelName, locationStr = None):
    model = YOLO(modelName)
    results = model.predict(source=src, conf=0.25)
    result = results[0]
    highConfSigns = []
    for box in result.boxes:
        signName = result.names[int(box.cls)]
        path = os.path.join(os.getcwd(), f"images/{signName}_Low_Confidence")
        if box.conf.item() >= 0.8:
            path = os.path.join(os.getcwd(), f"images/{signName}_High_Confidence")
            highConfSigns.append([signName, box.conf.item()])
            saveToTable = True
        os.makedirs(path, exist_ok = True)
        outputPath = f"{path}/{re.findall(r'streetview_frame_\d+_heading_\d+', src)[0]}.jpg"
        result.save(outputPath)
    return highConfSigns
            
        
def addToTable(filename, signName, location, url, confidence):
    item = {
    'SignName' : signName,
    'ImageURL' : url,
    'Location' : location,
    'Confidence' : confidence
    }
    fields = ['SignName', 'ImageURL', 'Location', 'Confidence']
    if(os.path.exists(filename)):
        with open(file = filename, mode = "a", newline='') as f:
            writer = csv.DictWriter(f, fieldnames = fields)
            writer.writerow(item)

    else:
        with open(file = filename, mode = "x", newline='') as f:
            writer = csv.DictWriter(f, fieldnames = fields)
            writer.writeheader()
            writer.writerow(item)


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
                        for sign, conf in found:
                            strippedurl = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch={pitchAngle}&key=#####&heading={fov*headingMult}&scale=2&radius=10&source=outdoor"
                            addToTable(f'tables/{datafile}', sign, locationStr, strippedurl, conf)
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
    os.makedirs(outputFolder, exist_ok = True)
    #max image size is 640x640
    imageSize = "640x640"
    fov = 60
    i=1

    #trim any points that are too close to each other
    route_points = trim_points_by_distance(route_points, minStep)


    #get pictures from the longitude latitude points using streetview api and save them
    for (log, lat) in route_points:
        locationStr = f"{log},{lat}"
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
                    found = detect_and_store(f"images/raw/streetview_frame_{i}_heading_{fov*headingMult}.jpg", f"models/{model}")
                    if(datafile != None):   
                        for sign, conf in found:
                            strippedurl = f"https://maps.googleapis.com/maps/api/streetview?size={imageSize}&location={locationStr}&fov={fov}&pitch={pitchAngle}&key=#####&heading={fov*headingMult}&scale=2&radius=10"
                            addToTable(f'tables/{datafile}', sign, locationStr, strippedurl, conf)
            except Exception as e:
                print(e)
        i+=1

