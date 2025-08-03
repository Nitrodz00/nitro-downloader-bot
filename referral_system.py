import logging
from typing import Dict, Any, Optional
from telegram import Bot
from telegram.error import TelegramError
from database import Database
from config import REFERRALS_REQUIRED, CHANNEL_ID, CHANNEL_USERNAME

class ReferralSystem:
    def __init__(self, bot: Bot, database: Database):
        self.bot = bot
        self.db = database
    
    async def check_channel_membership(self, user_id: int) -> bool:
        """Check if user is a member of the required channel"""
        try:
            member = await self.bot.get_chat_member(CHANNEL_ID, user_id)
            is_member = member.status in ['member', 'administrator', 'creator']
            
            # Update database with follow status
            self.db.set_channel_follow(user_id, is_member)
            
            return is_member
        except TelegramError as e:
            logging.error(f"Error checking channel membership for user {user_id}: {e}")
            return False
    
    def process_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Process a new referral"""
        # Don't allow self-referrals
        if referrer_id == referred_id:
            return False
        
        # Add the referral
        success = self.db.add_referral(referrer_id, referred_id)
        
        if success:
            # Check if referred user has made any downloads (activity verification)
            referred_user = self.db.get_user(referred_id)
            if referred_user and referred_user['downloads_used'] > 0:
                self.db.verify_referral(referrer_id, referred_id)
            
        return success
    
    def verify_referral_requirements(self, user_id: int) -> Dict[str, Any]:
        """Verify if user meets all referral requirements"""
        # Check referral count
        referral_count = self.db.get_referral_count(user_id)
        referrals_met = referral_count >= REFERRALS_REQUIRED
        
        # Check channel follow
        channel_followed = self.db.is_channel_followed(user_id)
        
        return {
            'referrals_count': referral_count,
            'referrals_required': REFERRALS_REQUIRED,
            'referrals_met': referrals_met,
            'channel_followed': channel_followed,
            'all_requirements_met': referrals_met and channel_followed
        }
    
    async def verify_and_grant_access(self, user_id: int) -> Dict[str, Any]:
        """Verify requirements and grant unlimited access if met"""
        # Re-check channel membership
        channel_followed = await self.check_channel_membership(user_id)
        
        # Get current status
        status = self.verify_referral_requirements(user_id)
        status['channel_followed'] = channel_followed
        status['all_requirements_met'] = status['referrals_met'] and channel_followed
        
        # Grant unlimited access if all requirements met
        if status['all_requirements_met']:
            user = self.db.get_user(user_id)
            if user and not user['unlimited_access']:
                self.db.grant_unlimited_access(user_id)
                status['access_granted'] = True
            else:
                status['access_granted'] = False
                status['already_unlimited'] = True
        else:
            status['access_granted'] = False
        
        return status
    
    def get_referral_link(self, user_id: int, bot_username: str) -> str:
        """Generate referral link for user"""
        return f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    def extract_referrer_from_start_param(self, start_param: str) -> Optional[int]:
        """Extract referrer ID from start parameter"""
        if start_param and start_param.startswith('ref_'):
            try:
                return int(start_param[4:])  # Remove 'ref_' prefix
            except ValueError:
                return None
        return None
    
    def auto_verify_active_referrals(self, user_id: int) -> int:
        """Auto-verify referrals for users who become active"""
        # This method is called when a user makes their first download
        # It verifies all pending referrals for this user
        
        try:
            # Find all unverified referrals where this user was referred
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT referrer_id FROM referrals 
                    WHERE referred_id = ? AND verified = FALSE
                ''', (user_id,))
                
                referrers = cursor.fetchall()
                verified_count = 0
                
                for (referrer_id,) in referrers:
                    if self.db.verify_referral(referrer_id, user_id):
                        verified_count += 1
                
                return verified_count
        except Exception as e:
            logging.error(f"Error auto-verifying referrals for user {user_id}: {e}")
            return 0
    
    def get_progress_message(self, user_id: int, bot_username: str) -> str:
        """Get formatted progress message for user"""
        status = self.verify_referral_requirements(user_id)
        referral_link = self.get_referral_link(user_id, bot_username)
        
        referrals_status = f"{status['referrals_count']}/{status['referrals_required']}"
        channel_status = "✅" if status['channel_followed'] else "❌"
        
        message = f"""
🎯 Unlock Unlimited Downloads Progress

📊 Current Status:
• Referrals: {referrals_status} {'✅' if status['referrals_met'] else '❌'}
• Channel Follow: {channel_status}

🔗 Your Referral Link:
{referral_link}

📋 Instructions:
1️⃣ Share your referral link with friends
2️⃣ Make sure they use the bot (download something)
3️⃣ Follow @{CHANNEL_USERNAME}
4️⃣ Use /verify to check progress

💡 Need {REFERRALS_REQUIRED - status['referrals_count']} more verified referrals!
"""
        
        if status['all_requirements_met']:
            message += "\n🎉 All requirements met! Use /verify to unlock unlimited access!"
        
        return message
