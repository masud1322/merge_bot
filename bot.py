import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from handlers.drive_handler import DriveHandler
from handlers.merge_handler import MergeHandler
from database.mongodb import MongoDB
from utils.helper import create_directories

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self):
        self.db = MongoDB()
        self.drive_handler = DriveHandler()
        self.merge_handler = MergeHandler(self.drive_handler, self.db)
        
    async def start(self, update, context):
        if not self.is_authorized(update):
            await update.message.reply_text("Sorry, you're not authorized to use this bot.")
            return
            
        await update.message.reply_text(
            "Hi! I'm a Video Merger Bot.\n"
            "Send me Google Drive video links and I'll merge them for you.\n"
            "Use /help to see available commands."
        )
    
    async def help(self, update, context):
        if not self.is_authorized(update):
            return
            
        help_text = """
Available Commands:
/start - Start the bot
/help - Show this help message
/us - Update settings (token.pickle or drive destination)
/merge - Start merging selected videos
/cancel - Cancel current operation
"""
        await update.message.reply_text(help_text)
    
    def is_authorized(self, update):
        user_id = update.effective_user.id
        return (user_id == Config.OWNER_ID or 
                user_id in Config.AUTHORIZED_CHATS)
    
    def run(self):
        application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(CommandHandler('us', self.merge_handler.settings))
        application.add_handler(CommandHandler('merge', self.merge_handler.merge))
        application.add_handler(CommandHandler('cancel', self.merge_handler.cancel))
        
        # Drive link handler
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.merge_handler.handle_drive_link
        ))
        
        # Callback queries
        application.add_handler(CallbackQueryHandler(self.merge_handler.button))
        
        # Start bot
        create_directories()
        application.run_polling()

if __name__ == '__main__':
    bot = Bot()
    bot.run() 