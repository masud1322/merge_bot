import os
import shutil
from config import Config

def create_directories():
    """Create necessary directories if they don't exist"""
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)

def clean_download_dir():
    """Clean the download directory"""
    if os.path.exists(Config.DOWNLOAD_DIR):
        shutil.rmtree(Config.DOWNLOAD_DIR)
        os.makedirs(Config.DOWNLOAD_DIR)

def get_readable_time(seconds: int) -> str:
    """Convert seconds to readable time format"""
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def get_readable_size(size_in_bytes: int) -> str:
    """Convert bytes to readable size format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB" 