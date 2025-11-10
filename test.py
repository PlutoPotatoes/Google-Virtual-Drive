import drive
from load_excel_and_test_ocr import load_excel

with open('secrets.txt') as f:
    API_KEY = f.readline().strip('\n')

#select start and finish locations using google maps addresses 
origin = "100 Main St 10th Floor, Los Angeles, CA 90012"
destination = "4884 Eagle Rock Blvd, Los Angeles, CA 90041"

# load the signs
unique_signs = load_excel()

#Use Routes API
drive.drive_route(origin, destination, API_KEY, minStep=30, fov = 90, datafile='tables/drive2.csv', ocr_candidate_signs=unique_signs)

#Use CSV Coordinates
#drive.csv_drive("GrandAv.csv", API_KEY, pitchAngle=5, fov=90, datafile='tables/drive1.csv')