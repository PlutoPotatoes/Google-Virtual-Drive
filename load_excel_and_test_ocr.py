# setup: install these libraries
# create service account credentials from Google Cloud and save the json keyfile in `credentials.json`
# tutorial: https://spreadsheetpoint.com/connect-python-and-google-sheets-15-minute-guide/
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# SHOULD NOT LOAD EXCEL THERE'S A BOUNDING BOX!!!
# maybe load once every iteration of drive

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

    # Fetch the first row of data
    # first_row = sheet.row_values(1)
    # print(f"First row of data: {first_row}")
    # ['Photo Assigned', 'Photo Collection Complete?', 'Model Assigned', 'Model Complete?', 'Model Complete date', 'OCR candidate?', 'Model Notes', 'Location of model Z:\\_Projects\\Asset_Recognition\\[folder name]', 'Bounding box name', 'Sign_Stock_No', 'Sub_Sign_Stock_No', '\nSign-Type', '', 'OCR Desc', 'DESCRIPTION', 'TABLE_ID', 'TYPE_OF_SIGNS', 'MUTCD_CODE', 'UNIQUE STOCK_NUMBER', 'UNIQUE STOCK_NUMBER_1', 'UNIQUE STOCK_NUMBER_2', 'ALT_DESC', 'IMAGE', 'ALT_IMAGE', '', 'assigned', 'model complete?', 'combine']
    # row = sheet.get_all_values() # list of all unique_signs as lists
    # print(unique_signs[0])
    # print(unique_signs[1])

unique_signs: list[dict] = load_excel()