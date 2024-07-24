import os.path
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import re
import html
import time

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1z5KN_JUGbCHoN7runYUzweeMlzpjmy5B2zlDiEI0ONk"
SAMPLE_RANGE_NAME = "Sheet1!A1:O2677"
WRITE_SPREADSHEET_ID = "1RWh93Og8plzmKV68DFhszjy7eu3RN_OHn3KVSr1VNzo"

def load():
    """Shows basic usage of the Sheets API to load and manipulate spreadsheet data."""
    creds = None
    
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=3000)
        
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        return load_sheet(creds, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
    except HttpError as err:
        print(err)

def load_sheet(credentials, spreadsheet_id, range_name):
    """Load data from a Google Spreadsheet into a pandas df."""
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()

    # Read data from the Google Spreadsheet
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get("values", [])

    if not values:
        print("No data found.")
        return pd.DataFrame()  # Return an empty DataFrame if no data found

    # Convert the data to a pandas DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])

   
    df = df[['nanonets_orginal_filename','Reference_to_map', 'Names_occupiers', 'Name_immediate_lessors', 'Description', 'Area', 'Annual_valuation_land',
             'AV_Buildings','Total_Valuation']]
    
    return df

def write_to_sheet(df, credentials, spreadsheet_id, range_name):
    """Write data from a pandas DataFrame to a Google Spreadsheet, clearing previous contents."""
    try:
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()

        df.fillna("N/A", inplace=True)


        sheet.values().clear(spreadsheetId=spreadsheet_id, range=range_name).execute()

        values = [df.columns.tolist()] + df.values.tolist()

        body = {
            'values': values
        }

        result = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()

        print("Data written successfully. Updated rows:", result.get('updatedRows'))
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise

def write(data, WRITE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
    """Initialize credentials and write data to a Google Spreadsheet."""
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentialsPost.json', SCOPES)
                creds = flow.run_local_server(port=3001)
                
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        write_to_sheet(data, creds, WRITE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
    except Exception as e:
        print(f"Failed to write to sheet: {e}")
        raise

    os.remove('./token.json')