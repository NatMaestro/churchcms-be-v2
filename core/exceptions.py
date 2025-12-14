"""
Custom exception handlers for FaithFlow Studio API.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.
    
    Returns:
        {
            "success": false,
            "error": "Error message",
            "details": {...},
            "status_code": 400
        }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'success': False,
            'error': response.data.get('detail', 'An error occurred'),
            'status_code': response.status_code,
        }
        
        # Add field-specific errors if they exist
        if isinstance(response.data, dict):
            errors = {
                key: value for key, value in response.data.items()
                if key != 'detail'
            }
            if errors:
                custom_response_data['details'] = errors
        
        response.data = custom_response_data
    
    return response


class TenantAccessDenied(Exception):
    """
    Exception raised when a user tries to access another tenant's data.
    """
    pass


class ChurchNotFound(Exception):
    """
    Exception raised when a church/tenant is not found.
    """
    pass


class InvalidSubdomain(Exception):
    """
    Exception raised when subdomain is invalid or already taken.
    """
    pass






