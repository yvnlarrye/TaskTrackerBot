import httplib2
import apiclient
from oauth2client.service_account import ServiceAccountCredentials

from google.config import SOURCE_SPREADSHEET, SHEETS_CREDENTIALS_FILE

spreadsheetId = SOURCE_SPREADSHEET

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    SHEETS_CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
)

httpAuth = credentials.authorize(httplib2.Http())
service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)


def append_row_in_table(table_name: str, row_range: str, values: list):
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheetId,
        range=f"'{table_name}'!{row_range}",
        valueInputOption="USER_ENTERED",
        body={
            "majorDimension": "ROWS",
            "values": values
        }
    ).execute()
