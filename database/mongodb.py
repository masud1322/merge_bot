from pymongo import MongoClient
from config import Config

class MongoDB:
    def __init__(self):
        self.client = MongoClient(Config.DATABASE_URL)
        self.db = self.client['video_merger']
        self.settings = self.db['settings']
        self.tasks = self.db['tasks']
    
    async def get_user_settings(self, user_id: int):
        return self.settings.find_one({'user_id': user_id}) or {
            'user_id': user_id,
            'drive_folder': Config.DRIVE_FOLDER_ID,
            'token_pickle': None
        }
    
    async def update_user_settings(self, user_id: int, settings: dict):
        return self.settings.update_one(
            {'user_id': user_id},
            {'$set': settings},
            upsert=True
        )
    
    async def save_task(self, user_id: int, task_data: dict):
        task_data['user_id'] = user_id
        return self.tasks.insert_one(task_data)
    
    async def get_user_tasks(self, user_id: int):
        return list(self.tasks.find({'user_id': user_id}))
    
    async def delete_task(self, task_id):
        return self.tasks.delete_one({'_id': task_id}) 