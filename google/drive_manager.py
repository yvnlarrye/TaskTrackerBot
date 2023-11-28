import datetime

from googleapiclient.http import MediaFileUpload
from google.google_service import Create_Service
from google.config import DRIVE_CREDENTIALS_FILE


def init_google_service():
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/drive']
    global service
    service = Create_Service(DRIVE_CREDENTIALS_FILE, API_NAME, API_VERSION, SCOPES)


def get_folder_files(folder_id) -> list:
    response = service.files().list(q=f"parents = '{folder_id}'").execute()
    root_folder_files = response.get('files')
    nextPageToken = response.get('nextPageToken')
    while nextPageToken:
        response = service.files().list(q=f"parents = '{folder_id}'").execute()
        root_folder_files.extend(response.get('files'))
        nextPageToken = response.get('nextPageToken')
    return root_folder_files


def upload_content(user: tuple, file_name: str, file_loc: str, root_folder_id: str) -> str:
    root_folder_files = get_folder_files(root_folder_id)
    user_folder = f"{user[0]}_{user[4]}_{user[5]}"
    for file in root_folder_files:
        if file.get('name') == user_folder:
            curr_folder_id = file.get('id')
            file_metadata = {
                'name': file_name,
                'parents': [curr_folder_id]
            }
            media = MediaFileUpload(file_loc, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            return f"https://drive.google.com/file/d/{file.get('id')}/view?usp=drive_link"

    # Creating user folder for file
    file_metadata = {
        'name': user_folder,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [root_folder_id]
    }
    folder = service.files().create(body=file_metadata).execute()

    # Putting file into folder
    file_metadata = {
        'name': file_name,
        'parents': [folder.get('id')]
    }
    media = MediaFileUpload(file_loc, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/file/d/{file.get('id')}/view?usp=drive_link"


def upload_report_photo(user: tuple, file_name: str, file_loc: str, root_folder_id: str) -> str:
    root_folder_files = get_folder_files(root_folder_id)

    user_folder = f"{user[0]}_{user[4]}_{user[5]}"
    day_folder_name = datetime.date.today().strftime("%d.%m.%Y")
    for file in root_folder_files:
        if file.get('name') == user_folder:
            user_folder_id = file.get('id')
            user_folder_files = get_folder_files(user_folder_id)
            for day_folder in user_folder_files:
                if day_folder.get('name') == day_folder_name:
                    day_folder_id = day_folder.get('id')
                    file_metadata = {
                        'name': file_name,
                        'parents': [day_folder_id]
                    }
                    media = MediaFileUpload(file_loc, resumable=True)
                    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                    return f"https://drive.google.com/drive/u/3/folders/{day_folder_id}"

            file_metadata = {
                'name': day_folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [user_folder_id]
            }
            day_folder = service.files().create(body=file_metadata).execute()
            day_folder_id = day_folder.get('id')
            file_metadata = {
                'name': file_name,
                'parents': [day_folder_id]
            }
            media = MediaFileUpload(file_loc, resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return f"https://drive.google.com/drive/u/3/folders/{day_folder_id}"

    file_metadata = {
        'name': user_folder,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [root_folder_id]
    }

    user_folder = service.files().create(body=file_metadata).execute()
    user_folder_id = user_folder.get('id')
    file_metadata = {
        'name': day_folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [user_folder_id]
    }
    day_folder = service.files().create(body=file_metadata).execute()
    day_folder_id = day_folder.get('id')
    file_metadata = {
        'name': file_name,
        'parents': [day_folder_id]
    }
    media = MediaFileUpload(file_loc, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/drive/u/3/folders/{day_folder_id}"
