import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple

class Database:
    def __init__(self, db_name: str = 'telegram_bot.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_name) as conn:
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
                
                # Downloads history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        platform TEXT,
                        url TEXT,
                        success BOOLEAN,
                        error_message TEXT,
                        download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Add a new user or update existing user info"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_activity)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user information"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, downloads_used, 
                           unlimited_access, joined_date, last_activity
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
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
            logging.error(f"Error getting user {user_id}: {e}")
            return None
    
    def increment_downloads(self, user_id: int) -> bool:
        """Increment user's download count"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET downloads_used = downloads_used + 1,
                                   last_activity = ?
                    WHERE user_id = ?
                ''', (datetime.now(), user_id))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error incrementing downloads for user {user_id}: {e}")
            return False
    
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Add a referral relationship"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO referrals (referrer_id, referred_id)
                    VALUES (?, ?)
                ''', (referrer_id, referred_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error adding referral {referrer_id} -> {referred_id}: {e}")
            return False
    
    def get_referral_count(self, user_id: int) -> int:
        """Get number of verified referrals for a user"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = ? AND verified = TRUE
                ''', (user_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting referral count for user {user_id}: {e}")
            return 0
    
    def verify_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Mark a referral as verified"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE referrals SET verified = TRUE
                    WHERE referrer_id = ? AND referred_id = ?
                ''', (referrer_id, referred_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error verifying referral {referrer_id} -> {referred_id}: {e}")
            return False
    
    def set_channel_follow(self, user_id: int, followed: bool = True) -> bool:
        """Set channel follow status for user"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO channel_follows 
                    (user_id, followed, verified_date)
                    VALUES (?, ?, ?)
                ''', (user_id, followed, datetime.now() if followed else None))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error setting channel follow for user {user_id}: {e}")
            return False
    
    def is_channel_followed(self, user_id: int) -> bool:
        """Check if user follows the channel"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT followed FROM channel_follows WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                return bool(result[0]) if result else False
        except Exception as e:
            logging.error(f"Error checking channel follow for user {user_id}: {e}")
            return False
    
    def grant_unlimited_access(self, user_id: int) -> bool:
        """Grant unlimited access to user"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET unlimited_access = TRUE
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error granting unlimited access to user {user_id}: {e}")
            return False
    
    def log_download(self, user_id: int, platform: str, url: str, 
                    success: bool, error_message: str = None) -> bool:
        """Log download attempt"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO downloads (user_id, platform, url, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, platform, url, success, error_message))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error logging download for user {user_id}: {e}")
            return False
    
    def get_download_stats(self, user_id: int) -> dict:
        """Get download statistics for user"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_downloads,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_downloads,
                        COUNT(DISTINCT platform) as platforms_used
                    FROM downloads WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                return {
                    'total_downloads': result[0],
                    'successful_downloads': result[1],
                    'platforms_used': result[2]
                }
        except Exception as e:
            logging.error(f"Error getting download stats for user {user_id}: {e}")
            return {'total_downloads': 0, 'successful_downloads': 0, 'platforms_used': 0}
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_name)
