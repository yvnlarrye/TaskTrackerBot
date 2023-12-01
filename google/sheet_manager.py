import apiclient
import gspread
import httplib2
from oauth2client.service_account import ServiceAccountCredentials

from data import config
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


def update_request_in_table(row_data: list):
    request_id = int(row_data[0])
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_key(spreadsheetId)
    cfg = config.get()
    request_sheet = spreadsheet.worksheet(cfg['request_sheet_name'])
    try:
        cell = request_sheet.find(str(request_id))
        row = cell.row
        request_sheet.update(f'A{row}:L{row}', [row_data])
    except Exception as ex:
        print(ex)
