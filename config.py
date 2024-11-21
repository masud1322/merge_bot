import os

class Config:
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
    OWNER_ID = int(os.environ.get('OWNER_ID', ''))
    AUTHORIZED_CHATS = set(int(x) for x in os.environ.get("AUTHORIZED_CHATS", "").split())
    
    # Port configuration
    PORT = int(os.environ.get('PORT', '8080'))
    
    # MongoDB
    DATABASE_URL = "mongodb+srv://mezbahasan07:HMhhlK9HBybT2km6@cluster0.f03zw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    # Drive
    DRIVE_FOLDER_ID = ""  # Default drive folder id
    
    # Download
    DOWNLOAD_DIR = "downloads"
    MAX_CONCURRENT_DOWNLOADS = 3
    MAX_MERGE_SIZE = 2000000000  # 2GB
    MAX_FILES = 10 