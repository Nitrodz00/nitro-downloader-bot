"""
Enhanced Telegram bot with improved Instagram downloads and referral system
"""

import os
import logging
import asyncio
import sqlite3
import time
import json
import re
import uuid
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import yt_dlp
import instaloader

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Database:
    """Database handler for user management and referrals"""
    
    def __init__(self, db_name='bot.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    downloads_used INTEGER DEFAULT 0,
                    unlimited_access BOOLEAN DEFAULT FALSE,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Referrals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_id) REFERENCES users (user_id),
                    UNIQUE(referrer_id, referred_id)
                )
            ''')
            
            # Channel follows table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channel_follows (
                    user_id INTEGER PRIMARY KEY,
                    followed BOOLEAN DEFAULT FALSE,
                    verified_date TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def add_user(self, user_id, username=None, first_name=None):
        """Add or update user"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_activity)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    def get_user(self, user_id):
        """Get user information"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, downloads_used, 
                       unlimited_access, joined_date, last_activity
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'first_name': result[2],
                    'downloads_used': result[3],
                    'unlimited_access': bool(result[4]),
                    'joined_date': result[5],
                    'last_activity': result[6]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    def increment_downloads(self, user_id):
        """Increment download count"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET downloads_used = downloads_used + 1,
                               last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error incrementing downloads for user {user_id}: {e}")
            return False
    
    def add_referral(self, referrer_id, referred_id):
        """Add referral relationship"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO referrals (referrer_id, referred_id)
                VALUES (?, ?)
            ''', (referrer_id, referred_id))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            logger.error(f"Error adding referral {referrer_id} -> {referred_id}: {e}")
            return False
    
    def get_referral_count(self, user_id):
        """Get verified referral count"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_id = ? AND verified = TRUE
            ''', (user_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting referral count for user {user_id}: {e}")
            return 0
    
    def verify_referral(self, referrer_id, referred_id):
        """Mark referral as verified"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE referrals SET verified = TRUE
                WHERE referrer_id = ? AND referred_id = ?
            ''', (referrer_id, referred_id))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            logger.error(f"Error verifying referral {referrer_id} -> {referred_id}: {e}")
            return False
    
    def set_channel_follow(self, user_id, followed=True):
        """Set channel follow status"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO channel_follows 
                (user_id, followed, verified_date)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, followed))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting channel follow for user {user_id}: {e}")
            return False
    
    def is_channel_followed(self, user_id):
        """Check if user follows channel"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT followed FROM channel_follows WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Error checking channel follow for user {user_id}: {e}")
            return False
    
    def grant_unlimited_access(self, user_id):
        """Grant unlimited access"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET unlimited_access = TRUE
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error granting unlimited access to user {user_id}: {e}")
            return False

class InstagramDownloader:
    """Enhanced Instagram downloader with multiple methods"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        })
        
        # Initialize instaloader
        try:
            self.loader = instaloader.Instaloader()
            self.loader.context.user_agent = 'Mozilla/5.0 (compatible; InstagramBot/1.0)'
        except Exception as e:
            logger.error(f"Error initializing instaloader: {e}")
            self.loader = None
    
    def extract_shortcode(self, url):
        """Extract Instagram shortcode from URL"""
        patterns = [
            r'instagram\.com/p/([A-Za-z0-9_-]+)',
            r'instagram\.com/reel/([A-Za-z0-9_-]+)',
            r'instagram\.com/tv/([A-Za-z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def download_with_instaloader(self, url, download_dir):
        """Download using instaloader"""
        if not self.loader:
            return None
            
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Generate unique filename
            unique_id = str(uuid.uuid4())[:8]
            
            if post.is_video:
                filename = f"{unique_id}_{post.owner_username}_video.mp4"
                filepath = os.path.join(download_dir, filename)
                
                # Download video
                video_response = self.session.get(post.video_url)
                with open(filepath, 'wb') as f:
                    f.write(video_response.content)
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'filename': filename,
                    'title': post.caption[:100] if post.caption else 'Instagram Video',
                    'file_size': os.path.getsize(filepath),
                    'platform': 'instagram',
                    'method': 'instaloader'
                }
            else:
                # For images
                filename = f"{unique_id}_{post.owner_username}_image.jpg"
                filepath = os.path.join(download_dir, filename)
                
                image_response = self.session.get(post.url)
                with open(filepath, 'wb') as f:
                    f.write(image_response.content)
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'filename': filename,
                    'title': post.caption[:100] if post.caption else 'Instagram Image',
                    'file_size': os.path.getsize(filepath),
                    'platform': 'instagram',
                    'method': 'instaloader'
                }
        except Exception as e:
            logger.error(f"Instaloader method failed: {e}")
            return None
    
    def download_with_scraping(self, url, download_dir):
        """Enhanced scraping method"""
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Multiple user agents to try
            user_agents = [
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Android 11; Mobile; rv:83.0) Gecko/83.0 Firefox/83.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]
            
            for user_agent in user_agents:
                headers = {
                    'User-Agent': user_agent,
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                }
                
                # Try different URL formats
                test_urls = [
                    url,
                    f"https://www.instagram.com/p/{shortcode}/",
                    f"https://www.instagram.com/reel/{shortcode}/"
                ]
                
                for test_url in test_urls:
                    try:
                        response = self.session.get(test_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            # Look for video URLs
                            patterns = [
                                r'"video_url":"([^"]+)"',
                                r'"video_versions":\[{"url":"([^"]+)"',
                                r'property="og:video:secure_url" content="([^"]+)"',
                                r'property="og:video" content="([^"]+)"'
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, response.text)
                                for match in matches:
                                    video_url = match.replace('\\u0026', '&').replace('\\/', '/')
                                    
                                    if video_url and ('mp4' in video_url or 'instagram' in video_url):
                                        # Download the video
                                        unique_id = str(uuid.uuid4())[:8]
                                        filename = f"{unique_id}_instagram_video.mp4"
                                        filepath = os.path.join(download_dir, filename)
                                        
                                        try:
                                            video_response = self.session.get(video_url, timeout=30)
                                            with open(filepath, 'wb') as f:
                                                f.write(video_response.content)
                                            
                                            return {
                                                'success': True,
                                                'filepath': filepath,
                                                'filename': filename,
                                                'title': 'Instagram Video',
                                                'file_size': os.path.getsize(filepath),
                                                'platform': 'instagram',
                                                'method': 'scraping'
                                            }
                                        except Exception as e:
                                            logger.error(f"Error downloading video: {e}")
                                            continue
                    except Exception as e:
                        logger.debug(f"URL {test_url} with agent {user_agent[:30]} failed: {e}")
                        continue
            
            return None
        except Exception as e:
            logger.error(f"Scraping method failed: {e}")
            return None
    
    def download(self, url, download_dir):
        """Main download method with fallbacks"""
        # Try instaloader first
        result = self.download_with_instaloader(url, download_dir)
        if result:
            return result
        
        # Try enhanced scraping
        result = self.download_with_scraping(url, download_dir)
        if result:
            return result
        
        return {
            'success': False,
            'error': 'Instagram content may be private, deleted, or require login'
        }

class EnhancedTelegramBot:
    """Enhanced Telegram bot with referral system and improved Instagram downloads"""
    
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Initialize database and Instagram downloader
        self.db = Database()
        self.instagram_downloader = InstagramDownloader()
        
        # Configuration
        self.free_downloads_limit = 5
        self.referrals_required = 5
        self.channel_username = 'NextGenTech2'
        self.channel_id = '@NextGenTech2'
        
        # Rate limiting for non-unlimited users
        self.user_downloads = {}
        self.max_downloads_per_hour = 10
        
        # Supported platforms
        self.supported_platforms = {
            'tiktok': ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com', 'm.tiktok.com'],
            'youtube': ['youtube.com', 'youtu.be', 'm.youtube.com'],
            'instagram': ['instagram.com', 'instagr.am', 'www.instagram.com'],
            'twitter': ['twitter.com', 'x.com', 't.co'],
            'facebook': ['facebook.com', 'fb.watch', 'm.facebook.com']
        }
    
    def get_updates(self):
        """Get updates from Telegram"""
        try:
            response = requests.get(f"{self.base_url}/getUpdates", 
                                  params={"offset": self.last_update_id + 1, "timeout": 30})
            return response.json()
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return None
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Send message to Telegram"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        try:
            response = requests.post(f"{self.base_url}/sendMessage", data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    def send_document(self, chat_id, document_path, caption=""):
        """Send document to Telegram"""
        try:
            with open(document_path, 'rb') as doc:
                files = {'document': doc}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'Markdown'
                }
                response = requests.post(f"{self.base_url}/sendDocument", files=files, data=data)
                return response.json()
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return None
    
    def send_video(self, chat_id, video_path, caption=""):
        """Send video to Telegram"""
        try:
            with open(video_path, 'rb') as video:
                files = {'video': video}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'Markdown'
                }
                response = requests.post(f"{self.base_url}/sendVideo", files=files, data=data)
                return response.json()
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            return None
    
    def check_channel_membership(self, user_id):
        """Check if user is member of required channel"""
        try:
            response = requests.get(f"{self.base_url}/getChatMember", 
                                  params={"chat_id": self.channel_id, "user_id": user_id})
            data = response.json()
            
            if data.get('ok'):
                status = data['result']['status']
                is_member = status in ['member', 'administrator', 'creator']
                self.db.set_channel_follow(user_id, is_member)
                return is_member
            return False
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            return False
    
    def detect_platform(self, url):
        """Detect platform from URL"""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            for platform, domains in self.supported_platforms.items():
                if any(domain.endswith(d) or domain == d for d in domains):
                    return platform
            return None
        except Exception:
            return None
    
    def extract_urls(self, text):
        """Extract URLs from text"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        
        # Also check for URLs without http/https
        domain_pattern = r'(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com|m\.tiktok\.com|youtube\.com|youtu\.be|m\.youtube\.com|instagram\.com|instagr\.am|twitter\.com|x\.com|t\.co|facebook\.com|fb\.watch|m\.facebook\.com)[\w\./\-?=&%]*'
        domain_urls = re.findall(domain_pattern, text, re.IGNORECASE)
        
        for url in domain_urls:
            if not url.startswith(('http://', 'https://')):
                urls.append(f'https://{url}')
        
        return list(set(urls))
    
    def can_download(self, user_id):
        """Check if user can download (rate limiting + download limits)"""
        user = self.db.get_user(user_id)
        if not user:
            return True  # New user, allow download
        
        # Unlimited users bypass all limits
        if user['unlimited_access']:
            return True
        
        # Check free download limit
        if user['downloads_used'] >= self.free_downloads_limit:
            return False
        
        # Check hourly rate limit for free users
        current_time = time.time()
        if user_id not in self.user_downloads:
            self.user_downloads[user_id] = []
        
        # Remove old entries
        self.user_downloads[user_id] = [
            timestamp for timestamp in self.user_downloads[user_id]
            if current_time - timestamp < 3600  # 1 hour
        ]
        
        return len(self.user_downloads[user_id]) < self.max_downloads_per_hour
    
    def record_download(self, user_id):
        """Record a download"""
        if user_id not in self.user_downloads:
            self.user_downloads[user_id] = []
        self.user_downloads[user_id].append(time.time())
        
        # Increment database counter and verify referrals for new users
        user = self.db.get_user(user_id)
        if user and user['downloads_used'] == 0:
            # First download - verify any pending referrals
            self.verify_pending_referrals(user_id)
        
        self.db.increment_downloads(user_id)
    
    def verify_pending_referrals(self, user_id):
        """Verify pending referrals when user becomes active"""
        try:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT referrer_id FROM referrals 
                WHERE referred_id = ? AND verified = FALSE
            ''', (user_id,))
            
            referrers = cursor.fetchall()
            for (referrer_id,) in referrers:
                self.db.verify_referral(referrer_id, user_id)
            
            conn.close()
        except Exception as e:
            logger.error(f"Error verifying pending referrals: {e}")
    
    def download_media(self, url):
        """Download media with enhanced Instagram support"""
        platform = self.detect_platform(url)
        
        if platform == 'instagram':
            return self.instagram_downloader.download(url, self.download_dir)
        
        # Use yt-dlp for other platforms
        unique_id = str(uuid.uuid4())[:8]
        
        options = {
            'format': 'best[filesize<50M]/best',
            'outtmpl': os.path.join(self.download_dir, f"{unique_id}_%(title)s.%(ext)s"),
            'noplaylist': True,
            'ignoreerrors': True,
            'no_warnings': False,
            'quiet': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'filesize' in info and info['filesize'] and info['filesize'] > 50 * 1024 * 1024:
                    return {
                        'success': False,
                        'error': 'File too large (max 50MB)'
                    }
                
                ydl.download([url])
                
                # Find downloaded file
                for file in os.listdir(self.download_dir):
                    if file.startswith(unique_id):
                        filepath = os.path.join(self.download_dir, file)
                        file_size = os.path.getsize(filepath)
                        
                        if file_size > 50 * 1024 * 1024:
                            os.remove(filepath)
                            return {
                                'success': False,
                                'error': 'Downloaded file too large'
                            }
                        
                        return {
                            'success': True,
                            'filepath': filepath,
                            'filename': file,
                            'title': info.get('title', 'Unknown'),
                            'file_size': file_size,
                            'platform': platform
                        }
                
                return {
                    'success': False,
                    'error': 'No file was downloaded'
                }
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def format_file_size(self, size_bytes):
        """Format file size"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    def get_platform_emoji(self, platform):
        """Get emoji for platform"""
        emojis = {
            'tiktok': '🎵 TikTok',
            'youtube': '🎬 YouTube',
            'instagram': '📸 Instagram',
            'twitter': '🐦 Twitter/X',
            'facebook': '📘 Facebook'
        }
        return emojis.get(platform, '🔗 Unknown Platform')
    
    def handle_start_command(self, message, args=None):
        """Handle /start command with referral support"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        username = message['from'].get('username')
        first_name = message['from'].get('first_name', 'User')
        
        # Add user to database
        self.db.add_user(user_id, username, first_name)
        
        # Check for referral parameter
        if args and args.startswith('ref_'):
            try:
                referrer_id = int(args[4:])  # Remove 'ref_' prefix
                if referrer_id != user_id:
                    success = self.db.add_referral(referrer_id, user_id)
                    if success:
                        # Notify referrer
                        try:
                            self.send_message(referrer_id, 
                                f"🎉 New referral! User {first_name} joined using your link!")
                        except:
                            pass
            except ValueError:
                pass
        
        # Get user status
        user = self.db.get_user(user_id)
        if user['unlimited_access']:
            downloads_status = "Unlimited"
        else:
            remaining = max(0, self.free_downloads_limit - user['downloads_used'])
            downloads_status = f"{remaining} free downloads remaining"
        
        welcome_text = f"""
🎉 **Welcome to NextGen Download Bot!**

Hi {first_name}! 👋

You can download videos and media from various platforms including:
• 🎵 TikTok
• 🎬 YouTube
• 📸 Instagram (Enhanced!)
• 🐦 Twitter/X
• 📘 Facebook

💡 **Status:** {downloads_status}

**How to get unlimited downloads:**
1. Share this bot with 5 friends
2. Follow our channel: @{self.channel_username}

Use /referral to start the process!
        """
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎁 Get Unlimited Access", "callback_data": "referral"}],
                [{"text": "📊 My Stats", "callback_data": "stats"}],
                [{"text": "📢 Follow Channel", "url": f"https://t.me/{self.channel_username}"}]
            ]
        }
        
        self.send_message(chat_id, welcome_text, keyboard)
    
    def handle_referral_command(self, message):
        """Handle /referral command"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # Get referral status
        referral_count = self.db.get_referral_count(user_id)
        channel_followed = self.db.is_channel_followed(user_id)
        
        # Generate referral link
        bot_username = "your_bot_username"  # Replace with actual bot username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        referral_text = f"""
🎯 **Get Unlimited Downloads!**

To unlock unlimited downloads:

1️⃣ **Share this bot with 5 friends**
   Send them this link: {referral_link}

2️⃣ **Follow our channel: @{self.channel_username}**
   Click here: https://t.me/{self.channel_username}

3️⃣ **Use /verify to check your progress**

**Current status:**
• Referrals: {referral_count}/{self.referrals_required} {'✅' if referral_count >= self.referrals_required else '❌'}
• Channel follow: {'✅' if channel_followed else '❌'}

💡 Your friends must actually use the bot (download something) for the referral to count!
        """
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Check Progress", "callback_data": "verify"}],
                [{"text": "📢 Follow Channel", "url": f"https://t.me/{self.channel_username}"}]
            ]
        }
        
        self.send_message(chat_id, referral_text, keyboard)
    
    def handle_verify_command(self, message):
        """Handle /verify command"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # Check channel membership
        channel_followed = self.check_channel_membership(user_id)
        referral_count = self.db.get_referral_count(user_id)
        
        all_requirements_met = referral_count >= self.referrals_required and channel_followed
        
        if all_requirements_met:
            user = self.db.get_user(user_id)
            if not user['unlimited_access']:
                self.db.grant_unlimited_access(user_id)
                verify_text = """
🎉 **Congratulations!**

You've successfully unlocked unlimited downloads! 🚀

✅ All requirements completed:
• Referrals: ✅
• Channel Follow: ✅

Enjoy unlimited downloads! 🎊
                """
            else:
                verify_text = "🎉 You already have unlimited access!"
        else:
            verify_text = f"""
📊 **Verification Results**

Current Progress:
• Referrals: {referral_count}/{self.referrals_required} {'✅' if referral_count >= self.referrals_required else '❌'}
• Channel Follow: {'✅' if channel_followed else '❌'}

"""
            if referral_count < self.referrals_required:
                needed = self.referrals_required - referral_count
                verify_text += f"📝 You need {needed} more verified referrals.\n"
            
            if not channel_followed:
                verify_text += f"📢 Please follow @{self.channel_username}\n"
            
            verify_text += "\n💡 Share your referral link and make sure friends use the bot!"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎁 Get Referral Link", "callback_data": "referral"}],
                [{"text": "📢 Follow Channel", "url": f"https://t.me/{self.channel_username}"}]
            ]
        }
        
        self.send_message(chat_id, verify_text, keyboard)
    
    def handle_stats_command(self, message):
        """Handle /stats command"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        user = self.db.get_user(user_id)
        if not user:
            self.send_message(chat_id, "❌ User not found. Please start the bot with /start")
            return
        
        referral_count = self.db.get_referral_count(user_id)
        channel_followed = self.db.is_channel_followed(user_id)
        
        if user['unlimited_access']:
            downloads_status = "♾️ Unlimited"
        else:
            remaining = max(0, self.free_downloads_limit - user['downloads_used'])
            downloads_status = f"{remaining}/{self.free_downloads_limit} remaining"
            
            # Also show hourly limit for free users
            current_time = time.time()
            if user_id in self.user_downloads:
                recent_downloads = [
                    t for t in self.user_downloads[user_id]
                    if current_time - t < 3600
                ]
                hourly_remaining = max(0, self.max_downloads_per_hour - len(recent_downloads))
            else:
                hourly_remaining = self.max_downloads_per_hour
            
            downloads_status += f"\n• This hour: {hourly_remaining}/{self.max_downloads_per_hour} remaining"
        
        stats_text = f"""
📊 **Your Statistics**

👤 **Account Info:**
• User ID: `{user_id}`
• Status: {'🌟 Premium' if user['unlimited_access'] else '🆓 Free'}

📥 **Downloads:**
• Available: {downloads_status}
• Total Used: {user['downloads_used']}

🎁 **Referral Progress:**
• Verified Referrals: {referral_count}/{self.referrals_required}
• Channel Follow: {'✅' if channel_followed else '❌'}

📱 **Supported Platforms:**
Instagram (Enhanced!), YouTube, TikTok, Twitter, Facebook
        """
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎁 Get Unlimited", "callback_data": "referral"}]
            ]
        }
        
        self.send_message(chat_id, stats_text, keyboard)
    
    def handle_message(self, message):
        """Handle incoming messages"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')
        
        # Handle commands
        if text.startswith('/start'):
            args = text.split(' ', 1)[1] if ' ' in text else None
            self.handle_start_command(message, args)
            return
        elif text.startswith('/referral'):
            self.handle_referral_command(message)
            return
        elif text.startswith('/verify'):
            self.handle_verify_command(message)
            return
        elif text.startswith('/stats'):
            self.handle_stats_command(message)
            return
        elif text.startswith('/help'):
            help_text = """
📖 **Help & Instructions**

**Supported Platforms:**
• TikTok - All video types
• YouTube - Videos, Shorts, Music
• Instagram - Posts, Stories, Reels (Enhanced!)
• Twitter/X - Videos, GIFs
• Facebook - Videos, Posts

**Usage:**
Simply send me any link from the supported platforms and I'll download the highest quality version available.

**Getting Unlimited Access:**
1. Share bot with 5 friends using /referral
2. Follow @NextGenTech2
3. Use /verify to unlock unlimited downloads

**Commands:**
/start - Welcome message
/help - This help message
/referral - Get unlimited access
/verify - Check referral progress
/stats - View your statistics
            """
            self.send_message(chat_id, help_text)
            return
        
        # Ensure user is in database
        username = message['from'].get('username')
        first_name = message['from'].get('first_name', 'User')
        self.db.add_user(user_id, username, first_name)
        
        # Extract URLs from message
        urls = self.extract_urls(text)
        supported_urls = [url for url in urls if self.detect_platform(url)]
        
        if not supported_urls:
            self.send_message(chat_id, """
❌ No supported URLs found.

Please send a link from:
• TikTok
• YouTube  
• Instagram
• Twitter/X
• Facebook
            """)
            return
        
        # Check download limits
        if not self.can_download(user_id):
            user = self.db.get_user(user_id)
            if user and not user['unlimited_access']:
                if user['downloads_used'] >= self.free_downloads_limit:
                    limit_text = f"""
❌ **You've reached your download limit!**

🎁 Get UNLIMITED downloads by:
1. Share this bot with 5 friends
2. Follow our channel: @{self.channel_username}

Use /referral to start the process!
                    """
                else:
                    limit_text = f"""
⏳ **Hourly rate limit exceeded!**

You've reached the maximum of {self.max_downloads_per_hour} downloads per hour.
Please try again later.

💡 Get unlimited downloads with /referral
                    """
                
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🎁 Get Unlimited Access", "callback_data": "referral"}]
                    ]
                }
                
                self.send_message(chat_id, limit_text, keyboard)
                return
        
        # Process first URL
        url = supported_urls[0]
        platform = self.detect_platform(url)
        
        # Send processing message
        processing_msg = self.send_message(chat_id, f"""
🔄 **Processing your request...**

Platform: {self.get_platform_emoji(platform)}
Status: Analyzing link...
        """)
        
        # Download media
        result = self.download_media(url)
        
        if result and result.get('success'):
            self.record_download(user_id)
            
            # Send file
            filepath = result['filepath']
            title = result['title'][:50]
            if len(result['title']) > 50:
                title += "..."
            
            caption = f"""
✅ **Download Complete!**

📱 **{title}**
📦 {self.format_file_size(result['file_size'])}
🔗 Platform: {result['platform'].title()}
            """
            
            # Add method info for Instagram
            if platform == 'instagram' and 'method' in result:
                caption += f"\n🔧 Method: {result['method']}"
            
            # Show remaining downloads for free users
            user = self.db.get_user(user_id)
            if user and not user['unlimited_access']:
                remaining = max(0, self.free_downloads_limit - user['downloads_used'])
                caption += f"\n📥 Downloads left: {remaining}"
                
                if remaining <= 2:
                    caption += "\n\n💡 Get unlimited downloads with /referral"
            
            # Determine file type and send accordingly
            file_ext = os.path.splitext(filepath)[1].lower()
            
            if file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
                self.send_video(chat_id, filepath, caption)
            else:
                self.send_document(chat_id, filepath, caption)
            
            # Clean up file
            try:
                os.remove(filepath)
            except:
                pass
        else:
            error_msg = result.get('error', 'Unknown error occurred') if result else 'Download failed unexpectedly'
            
            self.send_message(chat_id, f"""
❌ **Download Failed**

Error: {error_msg}

Please try again or contact support if the issue persists.
            """)
    
    def run(self):
        """Main bot loop"""
        logger.info("Starting NextGen Enhanced Download Bot...")
        
        while True:
            try:
                updates = self.get_updates()
                
                if updates and updates.get('ok'):
                    for update in updates['result']:
                        self.last_update_id = update['update_id']
                        
                        if 'message' in update:
                            self.handle_message(update['message'])
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)

def main():
    """Main function"""
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
        logger.error("Bot token not configured. Please set BOT_TOKEN environment variable.")
        return
    
    bot = EnhancedTelegramBot(bot_token)
    bot.run()

if __name__ == "__main__":
    main()