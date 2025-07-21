"""
Logging configuration for the application.
"""

import logging
import logging.config
import os
from typing import Dict, Any

def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Returns:
        Logging configuration dict
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "detailed")
    
    # Define formatters
    formatters = {
        "simple": {
            "format": "%(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "json": {
            "format": '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    }
    
    # Define handlers
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": log_format,
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": "logs/adaptiv.log",
            "mode": "a"
        }
    }
    
    # Define loggers
    loggers = {
        "adaptiv": {
            "level": log_level,
            "handlers": ["console", "file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False
        }
    }
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers,
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }

def setup_logging():
    """
    Setup logging configuration.
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Apply logging configuration
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Get logger for this module
    logger = logging.getLogger("adaptiv.config.logging")
    logger.info("Logging configuration initialized")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"adaptiv.{name}")

# Initialize logging when module is imported
if not logging.getLogger().handlers:
    setup_logging()
