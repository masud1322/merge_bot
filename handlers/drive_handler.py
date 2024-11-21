import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from config import Config
from utils.helper import get_readable_size
import re
import io

class DriveHandler:
    def __init__(self, db):
        self.service = None
        self.folder_id = Config.DRIVE_FOLDER_ID
        self.db = db
        self.connect()
    
    def connect(self):
        """Connect to Google Drive API"""
        try:
            # Try to get credentials from database first
            creds = self.get_credentials_from_db()
            
            if not creds and os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
                    
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Don't try to create new credentials, wait for user to provide token.pickle
                    return
                    
            self.service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Error connecting to Drive API: {str(e)}")
    
    def get_credentials_from_db(self):
        """Get credentials from database"""
        try:
            # Get token data from database
            settings = self.db.settings.find_one({'user_id': Config.OWNER_ID})
            if settings and settings.get('token_pickle'):
                return pickle.loads(settings['token_pickle'])
        except Exception as e:
            print(f"Error getting credentials from DB: {str(e)}")
        return None
    
    async def update_token(self, token_pickle_data: bytes):
        """Update token pickle in database"""
        try:
            # Save to database
            await self.db.update_user_settings(Config.OWNER_ID, {
                'token_pickle': token_pickle_data
            })
            
            # Load new credentials
            creds = pickle.loads(token_pickle_data)
            self.service = build('drive', 'v3', credentials=creds)
            return True
        except Exception as e:
            print(f"Error updating token: {str(e)}")
            return False
    
    async def update_folder_id(self, folder_id: str):
        """Update destination folder ID"""
        try:
            self.folder_id = folder_id
            await self.db.update_user_settings(Config.OWNER_ID, {
                'drive_folder': folder_id
            })
            return True
        except Exception as e:
            print(f"Error updating folder ID: {str(e)}")
            return False
    
    def is_valid_drive_link(self, link):
        patterns = [
            r'https://drive\.google\.com/file/d/(.*?)/',
            r'https://drive\.google\.com/open\?id=(.*?)$'
        ]
        for pattern in patterns:
            if match := re.search(pattern, link):
                return match.group(1)
        return None
    
    async def get_file_info(self, link):
        file_id = self.is_valid_drive_link(link)
        if not file_id:
            return None
            
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size'
            ).execute()
            
            is_video = file['mimeType'].startswith('video/')
            
            return {
                'id': file['id'],
                'name': file['name'],
                'size': int(file['size']),
                'readable_size': get_readable_size(int(file['size'])),
                'is_video': is_video
            }
        except Exception as e:
            print(f"Error getting file info: {str(e)}")
            return None
    
    async def download_file(self, file_id, path, progress_callback=None):
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status and progress_callback:
                    progress = status.progress() * 100
                    progress_callback(progress)
                    
            return True
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            return False
            
    async def upload_file(self, file_path, progress_callback=None):
        """Upload a file to Google Drive"""
        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.folder_id] if self.folder_id else None
            }
            
            media = MediaFileUpload(
                file_path,
                resumable=True,
                chunksize=1024*1024
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None
    
    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}" 