import requests
import re
import json
import logging
import asyncio
from typing import Optional, Dict, Any
import yt_dlp
import instaloader
from urllib.parse import urlparse, parse_qs

class InstagramDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.loader = instaloader.Instaloader()
        
        # Configure yt-dlp options
        self.ydl_opts = {
            'format': 'best[ext=mp4]',
            'noplaylist': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'quiet': True,
            'no_warnings': True,
        }
    
    def extract_shortcode(self, url: str) -> Optional[str]:
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
    
    async def download_with_yt_dlp(self, url: str) -> Optional[Dict[str, Any]]:
        """Download using yt-dlp"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    return {
                        'url': info.get('url'),
                        'title': info.get('title', 'Instagram Video'),
                        'thumbnail': info.get('thumbnail'),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'method': 'yt-dlp'
                    }
        except Exception as e:
            logging.error(f"yt-dlp download failed: {e}")
            return None
    
    async def download_with_instaloader(self, url: str) -> Optional[Dict[str, Any]]:
        """Download using instaloader"""
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Configure instaloader to avoid login requirements
            self.loader.context.user_agent = 'Mozilla/5.0 (compatible; InstagramBot/1.0)'
            
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            if post.is_video:
                return {
                    'url': post.video_url,
                    'title': post.caption[:100] if post.caption else 'Instagram Video',
                    'thumbnail': post.url,
                    'duration': post.video_duration,
                    'uploader': post.owner_username,
                    'method': 'instaloader'
                }
            else:
                # For images/carousels
                return {
                    'url': post.url,
                    'title': post.caption[:100] if post.caption else 'Instagram Image',
                    'thumbnail': post.url,
                    'uploader': post.owner_username,
                    'method': 'instaloader'
                }
        except instaloader.LoginRequiredException:
            logging.error("Instaloader requires login for this content")
            return None
        except instaloader.PrivateProfileNotFollowedException:
            logging.error("Content is from a private profile")
            return None
        except Exception as e:
            logging.error(f"Instaloader download failed: {e}")
            return None
    
    async def download_with_api(self, url: str) -> Optional[Dict[str, Any]]:
        """Download using alternative API method"""
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Method 1: Using Instagram's oembed API
            oembed_url = f"https://api.instagram.com/oembed/?url={url}"
            response = self.session.get(oembed_url)
            
            if response.status_code == 200:
                data = response.json()
                # Extract video URL from HTML if available
                html = data.get('html', '')
                video_match = re.search(r'video src="([^"]+)"', html)
                if video_match:
                    return {
                        'url': video_match.group(1),
                        'title': data.get('title', 'Instagram Video'),
                        'thumbnail': data.get('thumbnail_url'),
                        'uploader': data.get('author_name'),
                        'method': 'oembed'
                    }
            
            # Method 2: Direct scraping approach
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
            
            response = self.session.get(url, headers=headers)
            if response.status_code == 200:
                # Look for video URLs in the page source
                video_patterns = [
                    r'"video_url":"([^"]+)"',
                    r'"video_versions":\[{"url":"([^"]+)"',
                    r'property="og:video" content="([^"]+)"',
                    r'property="og:video:secure_url" content="([^"]+)"'
                ]
                
                for pattern in video_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        video_url = match.group(1).replace('\\u0026', '&')
                        
                        # Extract additional info
                        title_match = re.search(r'property="og:title" content="([^"]+)"', response.text)
                        title = title_match.group(1) if title_match else 'Instagram Video'
                        
                        thumbnail_match = re.search(r'property="og:image" content="([^"]+)"', response.text)
                        thumbnail = thumbnail_match.group(1) if thumbnail_match else None
                        
                        return {
                            'url': video_url,
                            'title': title,
                            'thumbnail': thumbnail,
                            'method': 'scraping'
                        }
            
            return None
        except Exception as e:
            logging.error(f"API download failed: {e}")
            return None
    
    async def download_with_rapidapi(self, url: str) -> Optional[Dict[str, Any]]:
        """Download using RapidAPI Instagram downloader"""
        try:
            # This would use a RapidAPI service for Instagram downloads
            # You would need to set up an API key in environment variables
            import os
            api_key = os.getenv('RAPIDAPI_KEY')
            
            if not api_key:
                return None
            
            headers = {
                'X-RapidAPI-Key': api_key,
                'X-RapidAPI-Host': 'instagram-downloader-download-instagram-videos-stories.p.rapidapi.com'
            }
            
            params = {'url': url}
            response = self.session.get(
                'https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index',
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    media = data.get('media', [])
                    if media:
                        item = media[0]
                        return {
                            'url': item.get('url'),
                            'title': data.get('title', 'Instagram Video'),
                            'thumbnail': item.get('thumbnail'),
                            'method': 'rapidapi'
                        }
            
            return None
        except Exception as e:
            logging.error(f"RapidAPI download failed: {e}")
            return None
    
    async def download_with_enhanced_scraping(self, url: str) -> Optional[Dict[str, Any]]:
        """Enhanced scraping method with multiple user agents and approaches"""
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Multiple user agents to try
            user_agents = [
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Android 11; Mobile; rv:83.0) Gecko/83.0 Firefox/83.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Instagram 219.0.0.12.117 Android'
            ]
            
            for user_agent in user_agents:
                try:
                    headers = {
                        'User-Agent': user_agent,
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    # Try different URL formats
                    urls_to_try = [
                        url,
                        f"https://www.instagram.com/p/{shortcode}/",
                        f"https://www.instagram.com/reel/{shortcode}/",
                        f"https://instagram.com/p/{shortcode}/"
                    ]
                    
                    for test_url in urls_to_try:
                        response = self.session.get(test_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            # Look for video URLs using multiple patterns
                            patterns = [
                                r'"video_url":"([^"]+)"',
                                r'"video_versions":\[{"url":"([^"]+)"',
                                r'property="og:video:secure_url" content="([^"]+)"',
                                r'property="og:video" content="([^"]+)"',
                                r'"playback_url":"([^"]+)"',
                                r'"src":"([^"]*\.mp4[^"]*)"',
                                r'videoUrl":"([^"]+)"',
                                r'"video_dash_manifest":"([^"]+)"'
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, response.text)
                                for match in matches:
                                    video_url = match.replace('\\u0026', '&').replace('\\/', '/')
                                    
                                    if video_url and ('mp4' in video_url or 'instagram' in video_url):
                                        # Extract additional metadata
                                        title_match = re.search(r'property="og:title" content="([^"]+)"', response.text)
                                        title = title_match.group(1) if title_match else 'Instagram Video'
                                        
                                        thumbnail_match = re.search(r'property="og:image" content="([^"]+)"', response.text)
                                        thumbnail = thumbnail_match.group(1) if thumbnail_match else None
                                        
                                        uploader_match = re.search(r'"username":"([^"]+)"', response.text)
                                        uploader = uploader_match.group(1) if uploader_match else 'Unknown'
                                        
                                        return {
                                            'url': video_url,
                                            'title': title,
                                            'thumbnail': thumbnail,
                                            'uploader': uploader,
                                            'method': f'enhanced_scraping_{user_agent[:20]}'
                                        }
                
                except Exception as e:
                    logging.debug(f"User agent {user_agent[:30]} failed: {e}")
                    continue
            
            return None
        except Exception as e:
            logging.error(f"Enhanced scraping failed: {e}")
            return None
    
    async def download(self, url: str) -> Dict[str, Any]:
        """Main download method with multiple fallbacks"""
        if not self.is_instagram_url(url):
            return {
                'success': False,
                'error': 'Not a valid Instagram URL'
            }
        
        # Try multiple methods in order of reliability
        methods = [
            self.download_with_enhanced_scraping,
            self.download_with_yt_dlp,
            self.download_with_instaloader,
            self.download_with_api,
            self.download_with_rapidapi
        ]
        
        for method in methods:
            try:
                result = await method(url)
                if result:
                    return {
                        'success': True,
                        'data': result
                    }
            except Exception as e:
                logging.error(f"Method {method.__name__} failed: {e}")
                continue
        
        return {
            'success': False,
            'error': 'All download methods failed. The content might be private, deleted, or require login.'
        }
    
    def is_instagram_url(self, url: str) -> bool:
        """Check if URL is from Instagram"""
        instagram_domains = ['instagram.com', 'www.instagram.com']
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() in instagram_domains
        except:
            return False
