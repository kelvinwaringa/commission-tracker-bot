"""
Configuration file for Commission Tracker Bot

Copy this file to config.py and fill in your values.
DO NOT commit config.py to version control!
"""

import os
from datetime import time

# Telegram Bot Token (set via environment variable or edit here)
# Get your token from @BotFather on Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "commissions.db")

# Timezone (default: Africa/Nairobi)
DEFAULT_TIMEZONE = os.getenv("TIMEZONE", "Africa/Nairobi")

# Scheduler Times
WEEKLY_SUMMARY_TIME = time(18, 0)  # Friday at 18:00
MONTH_END_SUMMARY_TIME = time(23, 0)  # Last day at 23:00
NEW_MONTH_START_TIME = time(0, 0)  # 1st day at 00:00
PAYOUT_REMINDER_TIME = time(18, 0)  # 28th at 18:00

# Safety Settings
UNDO_WINDOW_MINUTES = 5
DUPLICATE_DETECTION_MINUTES = 2
ZERO_ACTIVITY_DAYS = 7
EXTREME_AMOUNT_MULTIPLIER = 2.0  # Alert if >2x monthly average

# Split Settings
DEFAULT_SPLIT_USER = 0.5
DEFAULT_SPLIT_PARTNER = 0.5

# Authorization Settings
# Your Telegram User ID (get it from @userinfobot)
# This user will receive authorization requests and can approve/revoke users
OWNER_USER_ID = int(
    os.getenv("OWNER_USER_ID", "0")  # Set your user ID here or via environment variable
)
