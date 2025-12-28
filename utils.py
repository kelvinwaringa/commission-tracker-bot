"""
Utility functions for Commission Tracker Bot
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Tuple, Optional
import pytz
import config


def get_user_timezone(user_id: int = None) -> pytz.timezone:
    """Get user timezone (default: Africa/Nairobi)"""
    # For now, use default. Can be extended to fetch from database
    return pytz.timezone(config.DEFAULT_TIMEZONE)


def get_current_month_year(user_id: int = None) -> Tuple[str, int]:
    """Get current month and year in user's timezone"""
    tz = get_user_timezone(user_id)
    now = datetime.now(tz)
    return now.strftime("%Y-%m"), now.year


def parse_month_year(month_str: str = None) -> Tuple[str, int]:
    """Parse month string (YYYY-MM) or return current"""
    if month_str:
        try:
            parts = month_str.split("-")
            if len(parts) == 2:
                year = int(parts[0])
                month = parts[1]
                if len(month) == 1:
                    month = f"0{month}"
                return f"{year}-{month}", year
        except:
            pass
    return get_current_month_year()


def is_near_month_rollover(user_id: int = None, threshold_minutes: int = 5) -> bool:
    """Check if current time is near month rollover"""
    tz = get_user_timezone(user_id)
    now = datetime.now(tz)
    
    # Check if within threshold_minutes of midnight
    if now.hour == 0 and now.minute < threshold_minutes:
        return True
    if now.hour == 23 and now.minute >= (60 - threshold_minutes):
        return True
    return False


def generate_statement_id(user_id: int, month: str, year: int) -> str:
    """Generate immutable statement ID"""
    return f"STMT-{user_id}-{year}-{month}"


def format_kes(amount: Decimal) -> str:
    """Format amount as KES currency"""
    return f"KES {amount:,.2f}"


def format_number(num: float) -> str:
    """Format number with commas"""
    return f"{num:,.2f}"


def parse_amount(text: str) -> Optional[Decimal]:
    """Parse amount from text (number only)"""
    try:
        # Remove any non-numeric characters except decimal point
        cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
        if cleaned:
            return Decimal(cleaned)
    except:
        pass
    return None


def is_duplicate(amount: Decimal, recent_commissions: list, window_minutes: int = 2) -> bool:
    """Check if amount is duplicate within time window"""
    from dateutil import parser
    
    now = datetime.now(pytz.UTC)
    for comm in recent_commissions:
        try:
            comm_time = parser.parse(comm['date_added'])
            if isinstance(comm_time, datetime) and not comm_time.tzinfo:
                comm_time = pytz.UTC.localize(comm_time)
            
            time_diff = (now - comm_time).total_seconds() / 60
            
            if time_diff <= window_minutes and Decimal(comm['amount']) == amount:
                return True
        except:
            continue
    return False


def is_extreme_amount(amount: Decimal, monthly_average: Decimal, multiplier: float = 2.0) -> bool:
    """Check if amount is extreme (>multiplier x monthly average)"""
    if monthly_average == 0:
        return False
    return amount > (monthly_average * Decimal(str(multiplier)))


def get_days_active(commissions: list) -> int:
    """Get number of unique days with commission entries"""
    from dateutil import parser
    
    days = set()
    for comm in commissions:
        try:
            comm_time = parser.parse(comm['date_added'])
            days.add(comm_time.date())
        except:
            continue
    return len(days)


def get_weekly_totals(commissions: list) -> Dict[str, Decimal]:
    """Get weekly totals from commissions"""
    from dateutil import parser
    from collections import defaultdict
    
    weekly = defaultdict(Decimal)
    
    for comm in commissions:
        try:
            comm_time = parser.parse(comm['date_added'])
            if isinstance(comm_time, datetime) and not comm_time.tzinfo:
                comm_time = pytz.UTC.localize(comm_time)
            
            # Get week number
            week_key = f"Week {comm_time.isocalendar()[1]}"
            weekly[week_key] += Decimal(comm['amount'])
        except:
            continue
    
    return dict(weekly)


def get_daily_totals(commissions: list) -> Dict[str, Decimal]:
    """Get daily totals from commissions"""
    from dateutil import parser
    from collections import defaultdict
    
    daily = defaultdict(Decimal)
    
    for comm in commissions:
        try:
            comm_time = parser.parse(comm['date_added'])
            if isinstance(comm_time, datetime) and not comm_time.tzinfo:
                comm_time = pytz.UTC.localize(comm_time)
            
            day_key = comm_time.strftime("%Y-%m-%d")
            daily[day_key] += Decimal(comm['amount'])
        except:
            continue
    
    return dict(daily)

