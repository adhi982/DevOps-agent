"""
Test suite for utility functions.

Tests all utility functions to ensure they work correctly.
"""

import pytest
from datetime import datetime
from utils import (
    validate_number, 
    format_response, 
    sanitize_filename, 
    AppException, 
    handle_app_exception,
    get_config
)


class TestValidateNumber:
    """Test cases for validate_number function."""
    
    def test_valid_integers(self):
        """Test validation with valid integers."""
        assert validate_number(5) is True
        assert validate_number(0) is True
        assert validate_number(-10) is True
    
    def test_valid_floats(self):
        """Test validation with valid floats."""
        assert validate_number(3.14) is True
        assert validate_number(-2.5) is True
        assert validate_number(0.0) is True
    
    def test_valid_string_numbers(self):
        """Test validation with string representations of numbers."""
        assert validate_number("42") is True
        assert validate_number("3.14") is True
        assert validate_number("-5") is True
    
    def test_invalid_values(self):
        """Test validation with invalid values."""
        assert validate_number("not_a_number") is False
        assert validate_number("") is False
        assert validate_number(None) is False
        assert validate_number([1, 2, 3]) is False
        assert validate_number({"key": "value"}) is False


class TestFormatResponse:
    """Test cases for format_response function."""
    
    def test_success_response(self):
        """Test formatting successful response."""
        data = {"result": 42}
        response = format_response(data)
        
        assert response['status'] == 'success'
        assert response['data'] == data
        assert 'timestamp' in response
        assert isinstance(response['timestamp'], str)
    
    def test_error_response(self):
        """Test formatting error response."""
        response = format_response(None, status='error', message='Test error')
        
        assert response['status'] == 'error'
        assert response['data'] is None
        assert response['message'] == 'Test error'
        assert 'timestamp' in response
    
    def test_response_with_message(self):
        """Test response with custom message."""
        data = {"info": "test"}
        message = "Operation completed"
        response = format_response(data, message=message)
        
        assert response['status'] == 'success'
        assert response['data'] == data
        assert response['message'] == message


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""
    
    def test_safe_filename(self):
        """Test with already safe filename."""
        filename = "safe_filename.txt"
        result = sanitize_filename(filename)
        assert result == filename
    
    def test_dangerous_characters(self):
        """Test with dangerous characters."""
        filename = "file/../name.txt"
        result = sanitize_filename(filename)
        assert "../" not in result
        assert result == "file___name.txt"
    
    def test_multiple_dangerous_chars(self):
        """Test with multiple dangerous characters."""
        filename = 'file<>:"|?*.txt'
        result = sanitize_filename(filename)
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            assert char not in result
    
    def test_long_filename(self):
        """Test with very long filename."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")


class TestAppException:
    """Test cases for AppException class."""
    
    def test_exception_creation(self):
        """Test creating application exception."""
        message = "Test error"
        status_code = 400
        
        exception = AppException(message, status_code)
        
        assert exception.message == message
        assert exception.status_code == status_code
        assert str(exception) == message
    
    def test_default_status_code(self):
        """Test exception with default status code."""
        exception = AppException("Test error")
        assert exception.status_code == 500


class TestHandleAppException:
    """Test cases for handle_app_exception function."""
    
    def test_handle_exception(self):
        """Test handling application exception."""
        exception = AppException("Test error", 400)
        response = handle_app_exception(exception)
        
        assert response['status'] == 'error'
        assert response['message'] == 'Test error'
        assert response['data'] is None
        assert 'timestamp' in response


class TestGetConfig:
    """Test cases for get_config function."""
    
    def test_get_config_returns_dict(self):
        """Test that get_config returns a dictionary."""
        config = get_config()
        assert isinstance(config, dict)
    
    def test_config_has_required_keys(self):
        """Test that config contains required keys."""
        config = get_config()
        required_keys = ['SECRET_KEY', 'DEBUG', 'PORT', 'DATABASE_URL', 'API_BASE_URL']
        
        for key in required_keys:
            assert key in config
    
    def test_config_types(self):
        """Test that config values have correct types."""
        config = get_config()
        
        assert isinstance(config['SECRET_KEY'], str)
        assert isinstance(config['DEBUG'], bool)
        assert isinstance(config['PORT'], int)
        assert isinstance(config['DATABASE_URL'], str)
        assert isinstance(config['API_BASE_URL'], str)
