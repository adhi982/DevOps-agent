"""
Utility functions for the DevOps pipeline demo application.

This module contains helper functions and utilities used throughout
the application.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone


def setup_logging(level: str = 'INFO') -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def get_config() -> Dict[str, Any]:
    """
    Get application configuration from environment variables.
    
    Returns:
        Dictionary containing configuration values
    """
    return {
        'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key'),
        'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
        'PORT': int(os.getenv('PORT', 5000)),
        'DATABASE_URL': os.getenv('DATABASE_URL', 'sqlite:///app.db'),
        'API_BASE_URL': os.getenv('API_BASE_URL', 'https://api.example.com')
    }


def validate_number(value: Any) -> bool:
    """
    Validate if a value can be converted to a number.
    
    Args:
        value: Value to validate
        
    Returns:
        True if value is a valid number, False otherwise
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def format_response(data: Any, status: str = 'success', 
                   message: Optional[str] = None) -> Dict[str, Any]:
    """
    Format a standardized API response.
    
    Args:
        data: Response data
        status: Response status ('success' or 'error')
        message: Optional message
        
    Returns:
        Formatted response dictionary
    """
    response = {
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': data
    }
    
    if message:
        response['message'] = message
        
    return response


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing potentially dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:max_length - len(ext)] + ext
    
    return sanitized


class AppException(Exception):
    """Custom exception class for application errors."""
    
    def __init__(self, message: str, status_code: int = 500):
        """
        Initialize application exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def handle_app_exception(e: AppException) -> Dict[str, Any]:
    """
    Handle application exceptions and return formatted error response.
    
    Args:
        e: Application exception
        
    Returns:
        Formatted error response
    """
    return format_response(
        data=None,
        status='error',
        message=e.message
    )
