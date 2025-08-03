#!/usr/bin/env python3
"""
Simple test version to check if telegram-bot is working
"""
import logging
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_telegram_imports():
    """Test if telegram imports work"""
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
        from telegram.constants import ParseMode
        print("✅ All Telegram imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_other_imports():
    """Test other required imports"""
    try:
        import yt_dlp
        import instaloader
        import requests
        import sqlite3
        print("✅ All other imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

async def start_command(update: Update, context):
    """Handle /start command"""
    await update.message.reply_text("🎉 Bot is working! Send me a link to download media.")

async def help_command(update: Update, context):
    """Handle /help command"""
    help_text = """
🤖 NextGen Download Bot - Help

Supported platforms:
• Instagram (Posts, Reels, Stories)
• YouTube (Videos, Shorts)
• TikTok
• Twitter/X
• Facebook

Just send me a link and I'll download it for you!
    """
    await update.message.reply_text(help_text)

def main():
    """Main function to run the bot"""
    print("Testing imports...")
    
    if not test_telegram_imports():
        print("❌ Telegram imports failed!")
        return
    
    if not test_other_imports():
        print("❌ Other imports failed!")
        return
    
    # Check for bot token
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_bot_token_here':
        print("❌ Please set your BOT_TOKEN environment variable!")
        print("You can set it by running: export BOT_TOKEN='your_actual_bot_token'")
        return
    
    print(f"✅ Bot token found: {bot_token[:10]}...")
    
    try:
        from telegram.ext import Application, CommandHandler
        
        # Create application
        app = Application.builder().token(bot_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        
        print("🚀 Starting bot...")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == '__main__':
    main()