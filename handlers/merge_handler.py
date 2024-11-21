import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config
from utils.video import VideoMerger
from utils.progress import ProgressTracker
from utils.helper import get_readable_size

class MergeHandler:
    def __init__(self, drive_handler, db):
        self.drive_handler = drive_handler
        self.db = db
        self.merger = VideoMerger()
        self.user_files = {}  # Store selected files for each user
        self.progress = ProgressTracker()
        
    def is_authorized(self, update):
        user_id = update.effective_user.id
        return (user_id == Config.OWNER_ID or 
                user_id in Config.AUTHORIZED_CHATS)
        
    async def handle_drive_link(self, update, context):
        if not self.is_authorized(update):
            return
            
        user_id = update.effective_user.id
        link = update.message.text
        
        if not self.drive_handler.is_valid_drive_link(link):
            await update.message.reply_text("Please send a valid Google Drive link.")
            return
            
        file_info = await self.drive_handler.get_file_info(link)
        if not file_info:
            await update.message.reply_text("Unable to fetch file information.")
            return
            
        if not file_info['is_video']:
            await update.message.reply_text("Please send only video file links.")
            return
            
        # Initialize user files list if not exists
        if user_id not in self.user_files:
            self.user_files[user_id] = []
            
        if len(self.user_files[user_id]) >= Config.MAX_FILES:
            await update.message.reply_text(f"Maximum {Config.MAX_FILES} files allowed.")
            return
            
        # Add file to user's list
        self.user_files[user_id].append(file_info)
        
        # Calculate total size
        total_size = sum(f['size'] for f in self.user_files[user_id])
        
        keyboard = [
            [
                InlineKeyboardButton("Done", callback_data="merge_done"),
                InlineKeyboardButton("Cancel", callback_data="merge_cancel")
            ]
        ]
        
        await update.message.reply_text(
            f"File: {file_info['name']}\n"
            f"Size: {file_info['readable_size']}\n"
            f"Total files: {len(self.user_files[user_id])}\n"
            f"Total size: {get_readable_size(total_size)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def settings(self, update, context):
        if not self.is_authorized(update):
            return
        
        keyboard = [
            [
                InlineKeyboardButton("Update Token Pickle", callback_data="update_token"),
                InlineKeyboardButton("Drive Destination", callback_data="update_folder")
            ]
        ]
        
        await update.message.reply_text(
            "Choose what to update:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def button(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_authorized(update):
            await query.answer("Not authorized!")
            return
        
        await query.answer()
        
        if query.data == "update_token":
            await query.message.edit_text(
                "Please send me the token.pickle file"
            )
            context.user_data['awaiting_token'] = True
        
        elif query.data == "update_folder":
            await query.message.edit_text(
                "Please send me the Google Drive folder ID where files should be uploaded"
            )
            context.user_data['awaiting_folder'] = True
        
        elif query.data == "merge_done":
            if user_id not in self.user_files or not self.user_files[user_id]:
                await query.message.edit_text("No files selected!")
                return
            
            await query.message.edit_text("Please send the output filename (without extension)")
            context.user_data['awaiting_filename'] = True
        
        elif query.data == "merge_cancel":
            if user_id in self.user_files:
                del self.user_files[user_id]
            await query.message.edit_text("Operation cancelled!")

    async def merge(self, update, context):
        if not self.is_authorized(update):
            return
        
        user_id = update.effective_user.id
        if user_id not in self.user_files or not self.user_files[user_id]:
            await update.message.reply_text("No files selected for merging!")
            return
        
        filename = context.args[0] if context.args else f"merged_{user_id}"
        
        # Start the merge process
        status_message = await update.message.reply_text("Starting merge process...")
        
        try:
            # Download files
            downloaded_files = []
            for file_info in self.user_files[user_id]:
                file_path = os.path.join(Config.DOWNLOAD_DIR, file_info['name'])
                
                def progress_callback(progress):
                    return self.progress.update_progress(
                        progress, 100, status_message,
                        f"Downloading: {file_info['name']}"
                    )
                
                success = await self.drive_handler.download_file(
                    file_info['id'], file_path, progress_callback
                )
                
                if success:
                    downloaded_files.append(file_path)
                else:
                    await status_message.edit_text(f"Failed to download {file_info['name']}")
                    return

            # Merge videos
            output_path = await self.merger.merge_videos(downloaded_files, filename)
            if not output_path:
                await status_message.edit_text("Failed to merge videos!")
                return
            
            # Upload merged file
            await status_message.edit_text("Uploading merged video...")
            file_id = await self.drive_handler.upload_file(
                output_path,
                lambda p: self.progress.update_progress(
                    p, 100, status_message, "Uploading merged video"
                )
            )
            
            if file_id:
                share_link = f"https://drive.google.com/file/d/{file_id}/view"
                await status_message.edit_text(
                    f"Merge complete!\nFile: {filename}.mp4\nLink: {share_link}"
                )
            else:
                await status_message.edit_text("Failed to upload merged video!")
                
        except Exception as e:
            await status_message.edit_text(f"Error: {str(e)}")
            
        finally:
            # Cleanup
            if user_id in self.user_files:
                del self.user_files[user_id]