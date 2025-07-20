"""
Utility modules for the Dynamic Pricing backend.

This package contains various utility functions and classes that are used
throughout the application for common tasks like database operations,
session management, progress tracking, notifications, data conversion,
validation, datetime handling, and file operations.
"""

from .database_utils import DatabaseInterface
from .session_utils import SessionWrapper, get_session_wrapper
from .progress_utils import AgentProgress
from .notification_utils import KnockClient, knock_client
from .task_utils import running_tasks
from .data_utils import (
    convert_numpy_to_python,
    safe_convert_to_dict,
    format_json,
    normalize_array_field,
    clean_string,
    parse_numeric,
    convert_dates_to_strings,
    merge_dicts,
    flatten_dict
)
from .validation_utils import (
    validate_email,
    validate_positive_number,
    validate_positive_integer,
    validate_price,
    validate_percentage,
    validate_date_string,
    validate_required_fields,
    validate_string_length,
    validate_choice,
    validate_phone_number,
    validate_url,
    sanitize_string,
    validate_json_structure
)
from .datetime_utils import (
    get_current_utc,
    get_current_eastern,
    convert_to_utc,
    convert_from_utc,
    get_date_range,
    get_start_of_day,
    get_end_of_day,
    get_days_ago,
    format_datetime,
    parse_datetime,
    is_business_hours,
    get_week_start,
    get_month_start,
    get_quarter_start,
    get_year_start
)
from .file_utils import (
    ensure_directory_exists,
    get_temp_file_path,
    cleanup_old_files,
    write_csv_file,
    read_csv_file,
    write_json_file,
    read_json_file,
    get_file_size,
    get_file_modified_time,
    safe_filename,
    generate_timestamped_filename,
    get_csv_export_path,
    file_exists,
    directory_exists
)

__all__ = [
    # Database utilities
    "DatabaseInterface",
    
    # Session utilities
    "SessionWrapper", 
    "get_session_wrapper",
    
    # Progress tracking
    "AgentProgress",
    
    # Notification utilities
    "KnockClient",
    "knock_client",
    
    # Task utilities
    "running_tasks",
    
    # Data utilities
    "convert_numpy_to_python",
    "safe_convert_to_dict",
    "format_json",
    "normalize_array_field",
    "clean_string",
    "parse_numeric",
    "convert_dates_to_strings",
    "merge_dicts",
    "flatten_dict",
    
    # Validation utilities
    "validate_email",
    "validate_positive_number",
    "validate_positive_integer",
    "validate_price",
    "validate_percentage",
    "validate_date_string",
    "validate_required_fields",
    "validate_string_length",
    "validate_choice",
    "validate_phone_number",
    "validate_url",
    "sanitize_string",
    "validate_json_structure",
    
    # DateTime utilities
    "get_current_utc",
    "get_current_eastern",
    "convert_to_utc",
    "convert_from_utc",
    "get_date_range",
    "get_start_of_day",
    "get_end_of_day",
    "get_days_ago",
    "format_datetime",
    "parse_datetime",
    "is_business_hours",
    "get_week_start",
    "get_month_start",
    "get_quarter_start",
    "get_year_start",
    
    # File utilities
    "ensure_directory_exists",
    "get_temp_file_path",
    "cleanup_old_files",
    "write_csv_file",
    "read_csv_file",
    "write_json_file",
    "read_json_file",
    "get_file_size",
    "get_file_modified_time",
    "safe_filename",
    "generate_timestamped_filename",
    "get_csv_export_path",
    "file_exists",
    "directory_exists"
]
