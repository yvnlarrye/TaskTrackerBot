from googleapiclient.http import MediaFileUpload

from data.config import CONFIG
from google.Google import Create_Service

CLIENT_SECRET_FILE = 'google/client_secrets.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']


def upload_file_to_google_drive(user: tuple, file_name: str, file_loc: str) -> str:
    service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)
    root_folder_id = CONFIG['video_folder_id']

    response = service.files().list(q=f"parents = '{root_folder_id}'").execute()
    root_folder_files = response.get('files')
    nextPageToken = response.get('nextPageToken')

    while nextPageToken:
        response = service.files().list(q=f"parents = '{root_folder_id}'").execute()
        root_folder_files.extend(response.get('files'))
        nextPageToken = response.get('nextPageToken')

    user_folder = f"{user[0]}_{user[4]}_{user[5]}"
    for file in root_folder_files:
        if file.get('name') == user_folder:
            curr_folder_id = file.get('id')
            file_metadata = {
                'name': file_name,
                'parents': [curr_folder_id]
            }
            media = MediaFileUpload(file_loc, resumable=True)
            video = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            return f"https://drive.google.com/file/d/{video.get('id')}/view?usp=drive_link"

    # Creating user folder for video
    file_metadata = {
        'name': user_folder,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [root_folder_id]
    }
    folder = service.files().create(body=file_metadata).execute()

    # Putting video into folder
    file_metadata = {
        'name': file_name,
        'parents': [folder.get('id')]
    }
    media = MediaFileUpload(file_loc, resumable=True)
    video = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/file/d/{video.get('id')}/view?usp=drive_link"

