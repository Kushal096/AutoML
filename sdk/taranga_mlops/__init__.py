"""
Taranga MLOps SDK
A Python library for interacting with Taranga MLOps Platform
"""

from .client import TarangaClient
from .exceptions import TarangaError, AuthenticationError, APIError

__version__ = "1.0.0"
__all__ = ["TarangaClient", "TarangaError", "AuthenticationError", "APIError"]


