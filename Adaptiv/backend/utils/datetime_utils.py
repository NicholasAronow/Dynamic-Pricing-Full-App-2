"""
Date and time utilities for the Dynamic Pricing backend.
"""
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Union, List
import pytz


def get_current_utc() -> datetime:
    """
    Get the current UTC datetime.
    
    Returns:
        Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def get_current_eastern() -> datetime:
    """
    Get the current Eastern Time datetime.
    
    Returns:
        Current Eastern Time datetime with timezone info
    """
    eastern = pytz.timezone('US/Eastern')
    return datetime.now(eastern)


def convert_to_utc(dt: datetime, source_timezone: str = 'US/Eastern') -> datetime:
    """
    Convert a datetime to UTC.
    
    Args:
        dt: Datetime to convert
        source_timezone: Source timezone string
        
    Returns:
        UTC datetime with timezone info
    """
    if dt.tzinfo is None:
        # Assume source timezone if no timezone info
        source_tz = pytz.timezone(source_timezone)
        dt = source_tz.localize(dt)
    
    return dt.astimezone(timezone.utc)


def convert_from_utc(dt: datetime, target_timezone: str = 'US/Eastern') -> datetime:
    """
    Convert a UTC datetime to target timezone.
    
    Args:
        dt: UTC datetime to convert
        target_timezone: Target timezone string
        
    Returns:
        Datetime in target timezone
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    target_tz = pytz.timezone(target_timezone)
    return dt.astimezone(target_tz)


def get_date_range(start_date: Union[str, date, datetime], 
                   end_date: Union[str, date, datetime]) -> List[date]:
    """
    Get a list of dates between start and end dates (inclusive).
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        List of dates in the range
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    return dates


def get_start_of_day(dt: Union[datetime, date], timezone_str: str = 'US/Eastern') -> datetime:
    """
    Get the start of day (00:00:00) for a given date.
    
    Args:
        dt: Date or datetime
        timezone_str: Timezone string
        
    Returns:
        Datetime at start of day in specified timezone
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    tz = pytz.timezone(timezone_str)
    start_of_day = datetime.combine(dt, datetime.min.time())
    return tz.localize(start_of_day)


def get_end_of_day(dt: Union[datetime, date], timezone_str: str = 'US/Eastern') -> datetime:
    """
    Get the end of day (23:59:59.999999) for a given date.
    
    Args:
        dt: Date or datetime
        timezone_str: Timezone string
        
    Returns:
        Datetime at end of day in specified timezone
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    tz = pytz.timezone(timezone_str)
    end_of_day = datetime.combine(dt, datetime.max.time())
    return tz.localize(end_of_day)


def get_days_ago(days: int, timezone_str: str = 'US/Eastern') -> datetime:
    """
    Get a datetime that is a specified number of days ago.
    
    Args:
        days: Number of days ago
        timezone_str: Timezone string
        
    Returns:
        Datetime from days ago
    """
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    return now - timedelta(days=days)


def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format a datetime as a string.
    
    Args:
        dt: Datetime to format
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> Optional[datetime]:
    """
    Parse a datetime string.
    
    Args:
        dt_str: Datetime string to parse
        format_str: Format string
        
    Returns:
        Parsed datetime or None if parsing fails
    """
    try:
        return datetime.strptime(dt_str, format_str)
    except (ValueError, TypeError):
        return None


def is_business_hours(dt: datetime, 
                     start_hour: int = 9, 
                     end_hour: int = 17,
                     timezone_str: str = 'US/Eastern') -> bool:
    """
    Check if a datetime falls within business hours.
    
    Args:
        dt: Datetime to check
        start_hour: Business start hour (24-hour format)
        end_hour: Business end hour (24-hour format)
        timezone_str: Timezone string
        
    Returns:
        True if within business hours, False otherwise
    """
    # Convert to business timezone
    tz = pytz.timezone(timezone_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    else:
        dt = dt.astimezone(tz)
    
    # Check if weekday (Monday = 0, Sunday = 6)
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if within business hours
    return start_hour <= dt.hour < end_hour


def get_week_start(dt: Union[datetime, date], week_start: int = 0) -> date:
    """
    Get the start of the week for a given date.
    
    Args:
        dt: Date or datetime
        week_start: Day of week that starts the week (0=Monday, 6=Sunday)
        
    Returns:
        Date of the start of the week
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    days_since_start = (dt.weekday() - week_start) % 7
    return dt - timedelta(days=days_since_start)


def get_month_start(dt: Union[datetime, date]) -> date:
    """
    Get the start of the month for a given date.
    
    Args:
        dt: Date or datetime
        
    Returns:
        Date of the start of the month
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    return dt.replace(day=1)


def get_quarter_start(dt: Union[datetime, date]) -> date:
    """
    Get the start of the quarter for a given date.
    
    Args:
        dt: Date or datetime
        
    Returns:
        Date of the start of the quarter
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    quarter_month = ((dt.month - 1) // 3) * 3 + 1
    return dt.replace(month=quarter_month, day=1)


def get_year_start(dt: Union[datetime, date]) -> date:
    """
    Get the start of the year for a given date.
    
    Args:
        dt: Date or datetime
        
    Returns:
        Date of the start of the year
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    return dt.replace(month=1, day=1)
