import os

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')
CHANNEL_USERNAME = 'NextGenTech2'
CHANNEL_ID = '@NextGenTech2'

# Download Limits
FREE_DOWNLOADS_LIMIT = 5
REFERRALS_REQUIRED = 5

# Database Configuration
DATABASE_NAME = 'telegram_bot.db'

# Instagram Configuration
INSTAGRAM_PROXIES = [
    # Add proxies if needed for Instagram access
]

# Admin Configuration
ADMIN_IDS = [
    # Add admin user IDs here
]

# Messages
MESSAGES = {
    'welcome': """
🎉 Welcome to NextGen Download Bot!

You can download videos and media from various platforms including:
• YouTube
• Instagram
• TikTok
• Twitter
• And many more!

💡 You have {downloads_left} free downloads remaining.
""",
    'limit_exceeded': """
❌ You've reached your download limit!

🎁 Get UNLIMITED downloads by:
1. Share this bot with 5 friends
2. Follow our channel: @NextGenTech2

Use /referral to start the process!
""",
    'referral_instructions': """
🎯 Get Unlimited Downloads!

To unlock unlimited downloads:

1️⃣ Share this bot with 5 friends
   Send them this link: https://t.me/{bot_username}

2️⃣ Follow our channel: @NextGenTech2
   Click here: https://t.me/NextGenTech2

3️⃣ Use /verify to check your progress

Current status:
• Referrals: {referrals}/5
• Channel follow: {followed}
""",
    'download_success': """
✅ Download Complete!

Platform: {platform}
Downloads remaining: {downloads_left}
""",
    'download_failed': """
❌ Download Failed

Error: {error}

Please try again or contact support if the issue persists.
""",
    'processing': """
🔄 Processing your request...

Platform: {platform}
Status: Analyzing link...
"""
}
