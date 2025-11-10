from ultralytics import YOLO
import os
import re
import csv
import haversine as hs
from PIL import Image
from pyproj import Geod
import json
import cv2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from torchmetrics.text import CharErrorRate

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

def ocr(boxCoords, signName, src, crop_path, ocr, ocr_candidate_signs):
    newSignType = signName
    x1, y1, x2, y2 = boxCoords
    crop_img = cv2.imread(src)[int(y1):int(y2), int(x1):int(x2)]
    # Save cropped image
    cv2.imwrite(crop_path, crop_img)
    text_prediction = ocr.predict(crop_path)
    words = []
    # only one result
    for res in text_prediction: 
        res.save_to_json("images/temp/jsons/sign_name_data.json")
        with open("images/temp/jsons/sign_name_data.json", 'r', encoding='cp850') as f:
            j = json.load(f)
            # it may be worth pairing words with their confidence level
            words = j['rec_texts']
    lowest_cer, cers = specifySigns(signName, words, ocr_candidate_signs)
    os.remove("images/temp/jsons/sign_name_data.json")
    os.remove(crop_path)
    
    return lowest_cer

'''
def specifySigns(baseSign, words):
    signName = baseSign
    match(baseSign):
        case "Tow Away Signs Letters":
            print("Tow Away of some kind")
            #try to match all word in words to sign keywords
        case _:
            print("unidentified sign")
    return signName
'''

def load_excel():
    # Define the scope of API
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    # Authenticate with credentials
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)

    # Open the Google Sheet
    MASTER_SHEET_INDEX = 0
    sheet = client.open('Tracker - Merged Master Sign Catalog ').get_worksheet(MASTER_SHEET_INDEX)
    return sheet.get_all_records() # return all unique signs in the Google sheet

# have a list of ocr candidate
def specifySigns(baseSign, words, ocr_candidate_signs):
    cer = CharErrorRate()
    cers = {}
    prediction = " ".join(words)
    lowest_cer = ""
    # for each sign type
    for ocr_candidate_sign in ocr_candidate_signs:
        if (ocr_candidate_sign["Bounding box name"] == baseSign):
            ocr_desc = " ".join(ocr_candidate_sign["OCR Desc"].split('\n'))
            # calculate CER
            cer_val = cer(prediction, ocr_desc).item() / len(ocr_desc)
            if (len(cers) == 0 or (lowest_cer != "" and cer_val < cers[lowest_cer])):
                lowest_cer = ocr_desc
            cers[ocr_desc] = cer_val

    return lowest_cer, cers

def is_ocr_canditate(unique_sign):
    return unique_sign["OCR candidate?"] == "y"