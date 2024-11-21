import logging
import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from config import Config
from handlers.drive_handler import DriveHandler
from handlers.merge_handler import MergeHandler
from database.mongodb import MongoDB
from utils.helper import create_directories

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Bot:
    def __init__(self):
        """Initialize bot with required handlers"""
        self.db = MongoDB()
        self.drive_handler = DriveHandler(self.db)
        self.merge_handler = MergeHandler(self.drive_handler, self.db)
        self.application = None
        self.web_app = None
        self.stop_event = asyncio.Event()
        
    def is_authorized(self, update):
        """Check if user is authorized"""
        user_id = update.effective_user.id
        return (user_id == Config.OWNER_ID or 
                user_id in Config.AUTHORIZED_CHATS)
                
    async def start(self, update, context):
        """Start command handler"""
        if not self.is_authorized(update):
            await update.message.reply_text("Sorry, you're not authorized to use this bot.")
            return
            
        await update.message.reply_text(
            "Hi! I'm a Video Merger Bot.\n"
            "Send me Google Drive video links and I'll merge them for you.\n"
            "Use /help to see available commands."
        )
        
    async def help(self, update, context):
        """Help command handler"""
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
        
    async def restart(self, update, context):
        """Restart command handler"""
        if not self.is_authorized(update):
            return
            
        await update.message.reply_text("Restarting bot...")
        
        try:
            # Clear downloads directory
            for file in os.listdir(Config.DOWNLOAD_DIR):
                file_path = os.path.join(Config.DOWNLOAD_DIR, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
                    
            # Clear user files dictionary
            self.merge_handler.user_files.clear()
            
            # Reconnect to Drive API
            self.drive_handler.connect()
            
            await update.message.reply_text("Bot restarted successfully!")
            
        except Exception as e:
            await update.message.reply_text(f"Error during restart: {str(e)}")
            
    async def health_check(self, request):
        """Health check endpoint"""
        return web.Response(text="OK", status=200)
        
    async def run_web_server(self):
        """Run web server"""
        try:
            self.web_app = web.Application()
            self.web_app.router.add_get('/', self.health_check)
            
            runner = web.AppRunner(self.web_app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', Config.PORT)
            await site.start()
            
            logger.info("Web server started")
            
            # Keep running until stop event is set
            await self.stop_event.wait()
            
            # Cleanup
            await runner.cleanup()
            
        except Exception as e:
            logger.error(f"Web server error: {e}")
            self.stop_event.set()
            
    async def run_bot(self):
        """Run telegram bot"""
        try:
            # Create application
            self.application = Application.builder().token(Config.BOT_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler('start', self.start))
            self.application.add_handler(CommandHandler('help', self.help))
            self.application.add_handler(CommandHandler('us', self.merge_handler.settings))
            self.application.add_handler(CommandHandler('merge', self.merge_handler.merge))
            self.application.add_handler(CommandHandler('cancel', self.merge_handler.cancel))
            self.application.add_handler(CommandHandler('restart', self.restart))
            
            # Drive link handler
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.merge_handler.handle_drive_link
            ))
            
            # Callback queries
            self.application.add_handler(CallbackQueryHandler(self.merge_handler.button))
            
            # Handle document uploads (for token.pickle)
            self.application.add_handler(MessageHandler(
                filters.Document.ALL & ~filters.COMMAND,
                self.merge_handler.handle_token_pickle
            ))
            
            create_directories()
            
            # Start bot
            await self.application.initialize()
            logger.info("Bot started")
            
            # Run polling in a simpler way
            async with self.application:
                await self.application.start()
                await self.application.updater.start_polling(drop_pending_updates=True)
                
                # Keep the bot running
                while not self.stop_event.is_set():
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Bot error: {e}")
            self.stop_event.set()
            
        finally:
            # Cleanup
            if self.application:
                try:
                    await self.application.stop()
                    await self.application.shutdown()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
            
    async def run(self):
        """Run both web server and telegram bot"""
        try:
            # Run both services concurrently
            await asyncio.gather(
                self.run_web_server(),
                self.run_bot()
            )
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            # Ensure stop event is set
            self.stop_event.set()

def main():
    """Main function"""
    bot = Bot()
    
    # Run the bot with proper signal handling
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        loop.close()

if __name__ == '__main__':
    main() 