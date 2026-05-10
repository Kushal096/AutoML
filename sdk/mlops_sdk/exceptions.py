"""Custom exceptions for the MLOps SDK"""


class MLOpsError(Exception):
    """Base exception for the SDK"""
    pass


class AuthenticationError(MLOpsError):
    """Raised when authentication fails"""
    pass


class APIError(MLOpsError):
    """Raised when API request fails"""
    
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


