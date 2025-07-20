"""
Validation utilities for the Dynamic Pricing backend.
"""
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_positive_number(value: Any, allow_zero: bool = False) -> bool:
    """
    Validate that a value is a positive number.
    
    Args:
        value: Value to validate
        allow_zero: Whether to allow zero as valid
        
    Returns:
        True if value is a positive number, False otherwise
    """
    try:
        num = float(value)
        return num > 0 or (allow_zero and num >= 0)
    except (ValueError, TypeError):
        return False


def validate_positive_integer(value: Any, allow_zero: bool = False) -> bool:
    """
    Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        allow_zero: Whether to allow zero as valid
        
    Returns:
        True if value is a positive integer, False otherwise
    """
    try:
        if isinstance(value, float) and not value.is_integer():
            return False
        num = int(value)
        return num > 0 or (allow_zero and num >= 0)
    except (ValueError, TypeError):
        return False


def validate_price(price: Any) -> bool:
    """
    Validate that a value is a valid price (positive number with max 2 decimal places).
    
    Args:
        price: Price value to validate
        
    Returns:
        True if price is valid, False otherwise
    """
    try:
        decimal_price = Decimal(str(price))
        # Check if positive
        if decimal_price <= 0:
            return False
        # Check decimal places
        if decimal_price.as_tuple().exponent < -2:
            return False
        return True
    except (ValueError, TypeError, decimal.InvalidOperation):
        return False


def validate_percentage(value: Any, min_val: float = 0, max_val: float = 100) -> bool:
    """
    Validate that a value is a valid percentage within range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        True if value is a valid percentage, False otherwise
    """
    try:
        num = float(value)
        return min_val <= num <= max_val
    except (ValueError, TypeError):
        return False


def validate_date_string(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """
    Validate that a string is a valid date in the specified format.
    
    Args:
        date_str: Date string to validate
        format_str: Expected date format
        
    Returns:
        True if date string is valid, False otherwise
    """
    try:
        datetime.strptime(date_str, format_str)
        return True
    except (ValueError, TypeError):
        return False


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, List[str]]:
    """
    Validate that all required fields are present and not empty.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Dictionary with 'valid' boolean and 'missing_fields' list
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    return {
        'valid': len(missing_fields) == 0,
        'missing_fields': missing_fields
    }


def validate_string_length(value: str, min_length: int = 0, max_length: int = None) -> bool:
    """
    Validate string length constraints.
    
    Args:
        value: String to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length (None for no limit)
        
    Returns:
        True if string meets length requirements, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    length = len(value)
    
    if length < min_length:
        return False
    
    if max_length is not None and length > max_length:
        return False
    
    return True


def validate_choice(value: Any, choices: List[Any]) -> bool:
    """
    Validate that a value is one of the allowed choices.
    
    Args:
        value: Value to validate
        choices: List of allowed choices
        
    Returns:
        True if value is in choices, False otherwise
    """
    return value in choices


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format (basic validation).
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone number format is valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Check if it's all digits and reasonable length
    if not cleaned.isdigit():
        return False
    
    # Allow for country codes (7-15 digits)
    return 7 <= len(cleaned) <= 15


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL format is valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    return bool(re.match(pattern, url))


def sanitize_string(value: str, max_length: int = None) -> str:
    """
    Sanitize a string by removing potentially harmful characters.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Remove control characters and excessive whitespace
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Truncate if necessary
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    return sanitized


def validate_json_structure(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate JSON data against a simple schema.
    
    Args:
        data: Data to validate
        schema: Schema dictionary with field types
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    
    for field, expected_type in schema.items():
        if field in data:
            if not isinstance(data[field], expected_type):
                errors.append(f"Field '{field}' should be of type {expected_type.__name__}")
        else:
            errors.append(f"Missing required field: '{field}'")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
