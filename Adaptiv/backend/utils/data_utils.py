"""
Data conversion and manipulation utilities.
"""
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import numpy as np


def convert_numpy_to_python(obj: Any) -> Any:
    """
    Convert NumPy data types to native Python types for JSON serialization.
    
    Args:
        obj: Object that may contain NumPy types
        
    Returns:
        Object with NumPy types converted to Python types
    """
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_python(item) for item in obj)
    else:
        return obj


def safe_convert_to_dict(data: Any) -> Optional[Dict[str, Any]]:
    """
    Safely convert data to a dictionary, handling various input types.
    
    Args:
        data: Data to convert to dictionary
        
    Returns:
        Dictionary representation of the data, or None if conversion fails
    """
    if data is None:
        return None
        
    if isinstance(data, dict):
        return data
        
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return None
            
    if hasattr(data, '__dict__'):
        return data.__dict__
        
    return None


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as pretty-printed JSON string.
    
    Args:
        data: Data to format
        indent: Number of spaces for indentation
        
    Returns:
        Pretty-printed JSON string
    """
    try:
        # Convert NumPy types first
        converted_data = convert_numpy_to_python(data)
        return json.dumps(converted_data, indent=indent, default=str)
    except (TypeError, ValueError) as e:
        return f"Error formatting JSON: {str(e)}"


def normalize_array_field(data: Any) -> List[Any]:
    """
    Normalize a field that should be an array, ensuring it's always a list.
    
    Args:
        data: Data that should be an array
        
    Returns:
        List representation of the data
    """
    if data is None:
        return []
    elif isinstance(data, list):
        return data
    elif isinstance(data, (str, int, float, bool)):
        return [data]
    elif hasattr(data, '__iter__'):
        return list(data)
    else:
        return [data]


def clean_string(value: Optional[str]) -> Optional[str]:
    """
    Clean and normalize a string value.
    
    Args:
        value: String to clean
        
    Returns:
        Cleaned string or None
    """
    if not value or not isinstance(value, str):
        return None
    
    # Strip whitespace and normalize
    cleaned = value.strip()
    
    # Return None for empty strings
    if not cleaned:
        return None
        
    return cleaned


def parse_numeric(value: Any, default: Optional[Union[int, float]] = None) -> Optional[Union[int, float]]:
    """
    Parse a value as a numeric type (int or float).
    
    Args:
        value: Value to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed numeric value or default
    """
    if value is None:
        return default
        
    if isinstance(value, (int, float)):
        return value
        
    if isinstance(value, str):
        try:
            # Try int first
            if '.' not in value:
                return int(value)
            else:
                return float(value)
        except (ValueError, TypeError):
            return default
            
    return default


def convert_dates_to_strings(obj: Any) -> Any:
    """
    Convert datetime and date objects to ISO format strings for JSON serialization.
    
    Args:
        obj: Object that may contain datetime objects
        
    Returns:
        Object with datetime objects converted to strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_dates_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_dates_to_strings(item) for item in obj)
    else:
        return obj


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple dictionaries, with later dictionaries taking precedence.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
