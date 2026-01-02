#!/bin/bash
cd /workspace

# Create config.py from environment variables if it doesn't exist
if [ ! -f config.py ]; then
    cat > config.py << EOF
"""
Configuration file for Commission Tracker Bot
Generated at runtime from environment variables
"""

import os
from datetime import time

# Telegram Bot Token (from environment variable)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required! Set it as an environment variable.")

# Database - Use persistent storage if available, otherwise use workspace
# Koyeb persistent volumes are typically at /persistent or /data
import os.path
persistent_path = os.getenv("PERSISTENT_STORAGE_PATH", "/persistent")
if os.path.exists(persistent_path) and os.path.isdir(persistent_path):
    default_db_path = os.path.join(persistent_path, "commissions.db")
else:
    default_db_path = "commissions.db"
DATABASE_PATH = os.getenv("DATABASE_PATH", default_db_path)

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
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))
if OWNER_USER_ID == 0:
    raise ValueError("OWNER_USER_ID is required! Set it as an environment variable.")
EOF
fi

export PYTHONPATH=/workspace:$PYTHONPATH
python bot.py
