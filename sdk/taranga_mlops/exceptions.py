"""Custom exceptions for Taranga MLOps SDK"""


class TarangaError(Exception):
    """Base exception for Taranga SDK"""
    pass


class AuthenticationError(TarangaError):
    """Raised when authentication fails"""
    pass


class APIError(TarangaError):
    """Raised when API request fails"""
    
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


