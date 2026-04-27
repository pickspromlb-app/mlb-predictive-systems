from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from .settings import get_settings

def now_local() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))

def today_local() -> date:
    return now_local().date()

def yesterday_local() -> date:
    return today_local() - timedelta(days=1)
