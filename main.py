import logging
import asyncio
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

# Import our modules
from config import *
from database import Database
from instagram_downloader import InstagramDownloader
from referral_system import ReferralSystem
from utils import (
    detect_platform, extract_urls_from_text, download_with_ytdlp,
    format_duration, truncate_text, safe_send_message, safe_edit_message
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DownloadBot:
    def __init__(self):
        self.db = Database()
        self.instagram_downloader = InstagramDownloader()
        self.app = None
        self.referral_system = None
    
    async def post_init(self, application):
        """Post initialization after app is created"""
        self.referral_system = ReferralSystem(application.bot, self.db)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        # Add or update user in database
        self.db.add_user(user_id, user.username, user.first_name)
        
        # Check for referral parameter
        if context.args:
            start_param = context.args[0]
            referrer_id = self.referral_system.extract_referrer_from_start_param(start_param)
            
            if referrer_id and referrer_id != user_id:
                success = self.referral_system.process_referral(referrer_id, user_id)
                if success:
                    # Notify referrer
                    try:
                        await context.bot.send_message(
                            referrer_id,
                            f"🎉 New referral! User {user.first_name or user.username} joined using your link!"
                        )
                    except:
                        pass
        
        # Get user info and send welcome message
        user_data = self.db.get_user(user_id)
        downloads_left = max(0, FREE_DOWNLOADS_LIMIT - user_data['downloads_used']) if not user_data['unlimited_access'] else "Unlimited"
        
        welcome_text = MESSAGES['welcome'].format(downloads_left=downloads_left)
        
        keyboard = [
            [InlineKeyboardButton("📋 How to Use", callback_data="help")],
            [InlineKeyboardButton("🎁 Get Unlimited Access", callback_data="referral")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **NextGen Download Bot - Help**

**How to use:**
1. Send me any video/media link from supported platforms
2. I'll download and send it back to you!

**Supported Platforms:**
• Instagram (Posts, Reels, Stories)
• YouTube (Videos, Shorts)
• TikTok
• Twitter/X
• Facebook
• Vimeo
• And many more!

**Commands:**
/start - Start the bot
/help - Show this help message
/referral - Get unlimited downloads
/verify - Check referral progress
/stats - View your download statistics

**Download Limits:**
• Free users: {limit} downloads
• Unlimited access: Refer 5 friends + follow channel

**Need unlimited access?**
Use /referral to learn how to get unlimited downloads!

**Support:** @{channel}
        """.format(limit=FREE_DOWNLOADS_LIMIT, channel=CHANNEL_USERNAME)
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        user_id = update.effective_user.id
        bot_username = (await context.bot.get_me()).username
        
        message = self.referral_system.get_progress_message(user_id, bot_username)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Check Progress", callback_data="verify")],
            [InlineKeyboardButton("📢 Follow Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def verify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /verify command"""
        user_id = update.effective_user.id
        
        # Send processing message
        processing_msg = await update.message.reply_text("🔄 Verifying your progress...")
        
        # Verify requirements
        status = await self.referral_system.verify_and_grant_access(user_id)
        
        if status.get('already_unlimited'):
            message = "🎉 You already have unlimited access!"
        elif status.get('access_granted'):
            message = """
🎉 **Congratulations!** 

You've successfully unlocked unlimited downloads! 🚀

✅ All requirements completed:
• Referrals: {referrals}/{required}
• Channel Follow: ✅

Enjoy unlimited downloads! 🎊
            """.format(
                referrals=status['referrals_count'],
                required=status['referrals_required']
            )
        else:
            referrals_status = f"{status['referrals_count']}/{status['referrals_required']}"
            channel_status = "✅" if status['channel_followed'] else "❌"
            
            message = f"""
📊 **Verification Results**

Current Progress:
• Referrals: {referrals_status} {'✅' if status['referrals_met'] else '❌'}
• Channel Follow: {channel_status}

"""
            if not status['referrals_met']:
                needed = status['referrals_required'] - status['referrals_count']
                message += f"📝 You need {needed} more verified referrals.\n"
            
            if not status['channel_followed']:
                message += f"📢 Please follow @{CHANNEL_USERNAME}\n"
            
            message += "\n💡 Share your referral link and make sure friends use the bot!"
        
        keyboard = [
            [InlineKeyboardButton("🎁 Get Referral Link", callback_data="referral")],
            [InlineKeyboardButton("📢 Follow Channel", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(
            context.bot, update.effective_chat.id, processing_msg.message_id,
            message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        user_data = self.db.get_user(user_id)
        download_stats = self.db.get_download_stats(user_id)
        
        if user_data['unlimited_access']:
            downloads_status = "♾️ Unlimited"
        else:
            used = user_data['downloads_used']
            remaining = max(0, FREE_DOWNLOADS_LIMIT - used)
            downloads_status = f"{remaining}/{FREE_DOWNLOADS_LIMIT} remaining"
        
        # Get referral stats
        referral_count = self.db.get_referral_count(user_id)
        channel_followed = self.db.is_channel_followed(user_id)
        
        stats_text = f"""
📊 **Your Statistics**

👤 **Account Info:**
• User ID: `{user_id}`
• Joined: {user_data['joined_date'][:10]}
• Status: {'🌟 Premium' if user_data['unlimited_access'] else '🆓 Free'}

📥 **Downloads:**
• Available: {downloads_status}
• Total Downloads: {download_stats['total_downloads']}
• Successful: {download_stats['successful_downloads']}
• Platforms Used: {download_stats['platforms_used']}

🎁 **Referral Progress:**
• Verified Referrals: {referral_count}/{REFERRALS_REQUIRED}
• Channel Follow: {'✅' if channel_followed else '❌'}

📈 **Success Rate:** {
    f"{(download_stats['successful_downloads'] / download_stats['total_downloads'] * 100):.1f}%" 
    if download_stats['total_downloads'] > 0 else "N/A"
}
        """
        
        keyboard = [
            [InlineKeyboardButton("🎁 Get Unlimited", callback_data="referral")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            stats_text, 
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages with URLs"""
        user_id = update.effective_user.id
        user_data = self.db.get_user(user_id)
        
        if not user_data:
            self.db.add_user(user_id, update.effective_user.username, update.effective_user.first_name)
            user_data = self.db.get_user(user_id)
        
        # Check download limits
        if not user_data['unlimited_access']:
            if user_data['downloads_used'] >= FREE_DOWNLOADS_LIMIT:
                await update.message.reply_text(
                    MESSAGES['limit_exceeded'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎁 Get Unlimited Access", callback_data="referral")]
                    ])
                )
                return
        
        # Extract URLs from message
        urls = extract_urls_from_text(update.message.text)
        
        if not urls:
            await update.message.reply_text(
                "❌ No valid URLs found in your message.\n\n"
                "Please send a valid link from supported platforms:\n"
                "• Instagram\n• YouTube\n• TikTok\n• Twitter\n• And more!"
            )
            return
        
        # Process first URL found
        url = urls[0]
        platform = detect_platform(url)
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            MESSAGES['processing'].format(platform=platform)
        )
        
        try:
            # Download based on platform
            if 'Instagram' in platform:
                result = await self.instagram_downloader.download(url)
            else:
                result = await download_with_ytdlp(url)
            
            if result['success']:
                # Increment download count
                self.db.increment_downloads(user_id)
                
                # Auto-verify referrals for first-time users
                if user_data['downloads_used'] == 0:
                    self.referral_system.auto_verify_active_referrals(user_id)
                
                # Log successful download
                self.db.log_download(user_id, platform, url, True)
                
                # Get updated user data for downloads left
                updated_user = self.db.get_user(user_id)
                if updated_user['unlimited_access']:
                    downloads_left = "Unlimited"
                else:
                    downloads_left = max(0, FREE_DOWNLOADS_LIMIT - updated_user['downloads_used'])
                
                # Send download result
                data = result['data']
                title = truncate_text(data.get('title', 'Downloaded Video'))
                duration = format_duration(data.get('duration', 0))
                uploader = data.get('uploader', 'Unknown')
                
                success_text = f"""
✅ **Download Complete!**

📱 **Platform:** {platform}
🎬 **Title:** {title}
👤 **Uploader:** {uploader}
⏱️ **Duration:** {duration}
📥 **Downloads Left:** {downloads_left}

🔗 **Download Link:** [Click Here]({data['url']})
                """
                
                keyboard = []
                if downloads_left != "Unlimited" and downloads_left <= 2:
                    keyboard.append([InlineKeyboardButton("🎁 Get Unlimited", callback_data="referral")])
                
                await safe_edit_message(
                    context.bot, update.effective_chat.id, processing_msg.message_id,
                    success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            else:
                # Log failed download
                error_msg = result.get('error', 'Unknown error occurred')
                self.db.log_download(user_id, platform, url, False, error_msg)
                
                await safe_edit_message(
                    context.bot, update.effective_chat.id, processing_msg.message_id,
                    MESSAGES['download_failed'].format(error=error_msg)
                )
        
        except Exception as e:
            logger.error(f"Error processing download for user {user_id}: {e}")
            self.db.log_download(user_id, platform, url, False, str(e))
            
            await safe_edit_message(
                context.bot, update.effective_chat.id, processing_msg.message_id,
                MESSAGES['download_failed'].format(error="An unexpected error occurred. Please try again.")
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "help":
            await self.help_command(update, context)
        
        elif data == "referral":
            bot_username = (await context.bot.get_me()).username
            message = self.referral_system.get_progress_message(user_id, bot_username)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Check Progress", callback_data="verify")],
                [InlineKeyboardButton("📢 Follow Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("📊 My Stats", callback_data="stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
        
        elif data == "verify":
            # Simulate /verify command
            update.message = query.message
            await self.verify_command(update, context)
        
        elif data == "stats":
            # Simulate /stats command
            update.message = query.message
            await self.stats_command(update, context)
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to view bot statistics"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        # Get database statistics
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total users
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                # Users with unlimited access
                cursor.execute("SELECT COUNT(*) FROM users WHERE unlimited_access = 1")
                unlimited_users = cursor.fetchone()[0]
                
                # Total downloads
                cursor.execute("SELECT COUNT(*) FROM downloads")
                total_downloads = cursor.fetchone()[0]
                
                # Successful downloads
                cursor.execute("SELECT COUNT(*) FROM downloads WHERE success = 1")
                successful_downloads = cursor.fetchone()[0]
                
                # Total referrals
                cursor.execute("SELECT COUNT(*) FROM referrals WHERE verified = 1")
                total_referrals = cursor.fetchone()[0]
                
                # Platform stats
                cursor.execute("""
                    SELECT platform, COUNT(*) as count 
                    FROM downloads 
                    GROUP BY platform 
                    ORDER BY count DESC 
                    LIMIT 5
                """)
                platform_stats = cursor.fetchall()
                
                stats_text = f"""
📊 **Bot Admin Statistics**

👥 **Users:**
• Total Users: {total_users}
• Unlimited Access: {unlimited_users}
• Free Users: {total_users - unlimited_users}

📥 **Downloads:**
• Total Downloads: {total_downloads}
• Successful: {successful_downloads}
• Success Rate: {(successful_downloads/total_downloads*100):.1f if total_downloads > 0 else 'N/A'}%

🎁 **Referrals:**
• Verified Referrals: {total_referrals}

📱 **Top Platforms:**
"""
                
                for platform, count in platform_stats:
                    stats_text += f"• {platform}: {count}\n"
                
                await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error retrieving statistics: {e}")
    
    def run(self):
        """Run the bot"""
        # Create application
        self.app = Application.builder().token(BOT_TOKEN).post_init(self.post_init).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("referral", self.referral_command))
        self.app.add_handler(CommandHandler("verify", self.verify_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("admin_stats", self.admin_stats))
        
        # Message handler for URLs
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Run bot
        logger.info("Starting NextGen Download Bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = DownloadBot()
    bot.run()
