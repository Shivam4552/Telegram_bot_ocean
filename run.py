#!/usr/bin/env python3

import sys
import os
from pathlib import Path

def check_requirements():
    try:
        import telegram
        import cv2
        import PIL
        import dotenv
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_config():
    # Load environment variables directly (works on Railway)
    import os
    
    bot_token = os.getenv('BOT_TOKEN')
    admin_ids = os.getenv('ADMIN_IDS')
    channel_id = os.getenv('CHANNEL_ID')
    
    print(f"🔍 Checking environment variables...")
    print(f"BOT_TOKEN: {'✅ Set' if bot_token else '❌ Missing'}")
    print(f"ADMIN_IDS: {'✅ Set' if admin_ids else '❌ Missing'}")
    print(f"CHANNEL_ID: {'✅ Set' if channel_id else '❌ Missing'}")
    
    if not bot_token:
        print("❌ BOT_TOKEN not set in environment variables")
        return False
    
    if not admin_ids:
        print("❌ ADMIN_IDS not set in environment variables")
        return False
    
    if not channel_id:
        print("❌ CHANNEL_ID not set in environment variables")
        return False
    
    print("✅ All environment variables configured")
    return True

def main():
    print("🛡️ NEET Channel Moderation Bot v2.0")
    print("=" * 45)
    
    if not check_requirements():
        sys.exit(1)
    
    if not check_config():
        sys.exit(1)
    
    print("🚀 Starting bot...")
    
    try:
        from moderation_bot import ModerationBot
        print("📡 Connecting to Telegram...")
        bot = ModerationBot()
        print("✅ Connected successfully!")
        print("🤖 Bot is now running... (Press Ctrl+C to stop)")
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your internet connection")
        print("2. Verify bot token in .env file")
        print("3. Make sure bot isn't already running")
        sys.exit(1)

if __name__ == "__main__":
    main()