import logging
import os
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update
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
        self.drive_handler = DriveHandler(self.db)
        self.merge_handler = MergeHandler(self.drive_handler, self.db)
        
    async def health_check(self, request):
        """Health check endpoint"""
        return web.Response(text="OK", status=200)
        
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
/restart - Restart the bot
"""
        await update.message.reply_text(help_text)
    
    def is_authorized(self, update):
        user_id = update.effective_user.id
        return (user_id == Config.OWNER_ID or 
                user_id in Config.AUTHORIZED_CHATS)
    
    def run(self):
        """Run both web server and telegram bot"""
        import asyncio
        
        async def start_services():
            # Create web app for health check
            app = web.Application()
            app.router.add_get('/', self.health_check)
            
            # Create telegram bot application
            application = Application.builder().token(Config.BOT_TOKEN).build()
            
            # Add handlers
            application.add_handler(CommandHandler('start', self.start))
            application.add_handler(CommandHandler('help', self.help))
            application.add_handler(CommandHandler('us', self.merge_handler.settings))
            application.add_handler(CommandHandler('merge', self.merge_handler.merge))
            application.add_handler(CommandHandler('cancel', self.merge_handler.cancel))
            application.add_handler(CommandHandler('restart', self.restart))
            
            # Drive link handler
            application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.merge_handler.handle_drive_link
            ))
            
            # Callback queries
            application.add_handler(CallbackQueryHandler(self.merge_handler.button))
            
            # Handle document uploads (for token.pickle)
            application.add_handler(MessageHandler(
                filters.Document.ALL & ~filters.COMMAND,
                self.merge_handler.handle_token_pickle
            ))
            
            # Start bot
            create_directories()
            
            # Start web server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', Config.PORT)
            await site.start()
            
            # Start bot
            await application.initialize()
            await application.start()
            await application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the services
        try:
            loop.run_until_complete(start_services())
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    
    async def restart(self, update, context):
        if not self.is_authorized(update):
            return
        
        await update.message.reply_text("Restarting bot...")
        
        # Cleanup
        try:
            # Clear downloads directory
            for file in os.listdir(Config.DOWNLOAD_DIR):
                file_path = os.path.join(Config.DOWNLOAD_DIR, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
                
            # Clear user files dictionary
            self.merge_handler.user_files.clear()
            
            # Reconnect to Drive API
            self.drive_handler.connect()
            
            await update.message.reply_text("Bot restarted successfully!")
            
        except Exception as e:
            await update.message.reply_text(f"Error during restart: {str(e)}")

if __name__ == '__main__':
    bot = Bot()
    bot.run() 