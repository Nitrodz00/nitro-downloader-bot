import re
import logging
import asyncio
from typing import Optional, Dict, Any
import yt_dlp
from urllib.parse import urlparse

def detect_platform(url: str) -> str:
    """Detect the platform from URL"""
    url = url.lower()
    
    if 'instagram.com' in url:
        return '📸 Instagram'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return '🎥 YouTube'
    elif 'tiktok.com' in url:
        return '🎵 TikTok'
    elif 'twitter.com' in url or 'x.com' in url:
        return '🐦 Twitter'
    elif 'facebook.com' in url or 'fb.com' in url:
        return '📘 Facebook'
    elif 'vimeo.com' in url:
        return '🎬 Vimeo'
    elif 'dailymotion.com' in url:
        return '📺 Dailymotion'
    elif 'twitch.tv' in url:
        return '🎮 Twitch'
    else:
        return '🌐 Other Platform'

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def extract_urls_from_text(text: str) -> list:
    """Extract URLs from text"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    urls = url_pattern.findall(text)
    return [url for url in urls if is_valid_url(url)]

async def download_with_ytdlp(url: str) -> Dict[str, Any]:
    """Download using yt-dlp for non-Instagram platforms"""
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'noplaylist': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ydl.extract_info(url, download=False)
            )
            
            if info:
                return {
                    'success': True,
                    'data': {
                        'url': info.get('url'),
                        'title': info.get('title', 'Downloaded Video'),
                        'thumbnail': info.get('thumbnail'),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'platform': info.get('extractor_key', 'Unknown'),
                        'method': 'yt-dlp'
                    }
                }
    except Exception as e:
        logging.error(f"yt-dlp download failed for {url}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format"""
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if not text:
        return "No title"
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format"""
    if not size_bytes:
        return "Unknown size"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def clean_filename(filename: str) -> str:
    """Clean filename for safe file operations"""
    # Remove invalid characters for filenames
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def is_admin(user_id: int, admin_ids: list) -> bool:
    """Check if user is admin"""
    return user_id in admin_ids

async def safe_send_message(bot, chat_id: int, text: str, **kwargs):
    """Safely send message with error handling"""
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logging.error(f"Error sending message to {chat_id}: {e}")
        return None

async def safe_edit_message(bot, chat_id: int, message_id: int, text: str, **kwargs):
    """Safely edit message with error handling"""
    try:
        return await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            **kwargs
        )
    except Exception as e:
        logging.error(f"Error editing message {message_id} in {chat_id}: {e}")
        return None
