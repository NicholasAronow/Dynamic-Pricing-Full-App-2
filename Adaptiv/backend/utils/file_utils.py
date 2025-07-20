"""
File handling utilities for the Dynamic Pricing backend.
"""
import os
import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def ensure_directory_exists(directory_path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_file_path(suffix: str = '', prefix: str = 'temp_', directory: str = None) -> str:
    """
    Get a temporary file path.
    
    Args:
        suffix: File suffix/extension
        prefix: File prefix
        directory: Directory for temp file (None for system temp)
        
    Returns:
        Path to temporary file
    """
    if directory:
        ensure_directory_exists(directory)
    
    with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, dir=directory, delete=False) as f:
        return f.name


def cleanup_old_files(directory: Union[str, Path], 
                     max_age_hours: int = 24,
                     pattern: str = '*') -> int:
    """
    Clean up old files in a directory.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files to keep (in hours)
        pattern: File pattern to match
        
    Returns:
        Number of files deleted
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        return 0
    
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    deleted_count = 0
    
    try:
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up files in {directory}: {e}")
    
    return deleted_count


def write_csv_file(file_path: Union[str, Path], 
                   data: List[Dict[str, Any]], 
                   fieldnames: Optional[List[str]] = None) -> bool:
    """
    Write data to a CSV file.
    
    Args:
        file_path: Path to the CSV file
        data: List of dictionaries to write
        fieldnames: List of field names (auto-detected if None)
        
    Returns:
        True if successful, False otherwise
    """
    if not data:
        return False
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        return True
    except Exception as e:
        logger.error(f"Error writing CSV file {file_path}: {e}")
        return False


def read_csv_file(file_path: Union[str, Path]) -> Optional[List[Dict[str, Any]]]:
    """
    Read data from a CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        return None


def write_json_file(file_path: Union[str, Path], data: Any, indent: int = 2) -> bool:
    """
    Write data to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: Data to write
        indent: JSON indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=indent, default=str)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file {file_path}: {e}")
        return False


def read_json_file(file_path: Union[str, Path]) -> Optional[Any]:
    """
    Read data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON data or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            return json.load(jsonfile)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return None


def get_file_size(file_path: Union[str, Path]) -> Optional[int]:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes or None if error
    """
    try:
        return Path(file_path).stat().st_size
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return None


def get_file_modified_time(file_path: Union[str, Path]) -> Optional[datetime]:
    """
    Get the last modified time of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Last modified datetime or None if error
    """
    try:
        timestamp = Path(file_path).stat().st_mtime
        return datetime.fromtimestamp(timestamp)
    except Exception as e:
        logger.error(f"Error getting file modified time for {file_path}: {e}")
        return None


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Create a safe filename by removing/replacing problematic characters.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Safe filename
    """
    # Remove or replace problematic characters
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    safe_name = ''.join(c if c in safe_chars else '_' for c in filename)
    
    # Remove multiple consecutive underscores
    while '__' in safe_name:
        safe_name = safe_name.replace('__', '_')
    
    # Trim to max length
    if len(safe_name) > max_length:
        name, ext = os.path.splitext(safe_name)
        max_name_length = max_length - len(ext)
        safe_name = name[:max_name_length] + ext
    
    return safe_name


def generate_timestamped_filename(base_name: str, extension: str = '', timestamp_format: str = '%Y%m%d_%H%M%S') -> str:
    """
    Generate a filename with timestamp.
    
    Args:
        base_name: Base filename
        extension: File extension (with or without dot)
        timestamp_format: Timestamp format string
        
    Returns:
        Timestamped filename
    """
    timestamp = datetime.now().strftime(timestamp_format)
    
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    return f"{base_name}_{timestamp}{extension}"


def get_csv_export_path(user_id: int, export_type: str, base_dir: str = '/tmp/csv_exports') -> str:
    """
    Generate a path for CSV export files.
    
    Args:
        user_id: User ID
        export_type: Type of export (e.g., 'menu_items', 'orders')
        base_dir: Base directory for exports
        
    Returns:
        Path to CSV export file
    """
    ensure_directory_exists(base_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"user_{user_id}_{export_type}_{timestamp}.csv"
    return os.path.join(base_dir, filename)


def file_exists(file_path: Union[str, Path]) -> bool:
    """
    Check if a file exists.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).is_file()


def directory_exists(directory_path: Union[str, Path]) -> bool:
    """
    Check if a directory exists.
    
    Args:
        directory_path: Path to check
        
    Returns:
        True if directory exists, False otherwise
    """
    return Path(directory_path).is_dir()
