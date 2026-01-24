"""
Custom exception classes for structured error handling
"""
from typing import Optional, Dict, Any
from fastapi import status


class AppException(Exception):
    """Base exception class for all application exceptions"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error - 400 Bad Request"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(AppException):
    """Authentication error - 401 Unauthorized"""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(AppException):
    """Authorization error - 403 Forbidden"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class NotFoundError(AppException):
    """Resource not found error - 404 Not Found"""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (id: {resource_id})"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details or {"resource": resource, "resource_id": resource_id}
        )


class BusinessLogicError(AppException):
    """Business logic error - 400 Bad Request or 422 Unprocessable Entity"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details
        )


class ConflictError(AppException):
    """Resource conflict error - 409 Conflict"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
            details=details
        )


class ServerError(AppException):
    """Internal server error - 500 Internal Server Error"""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SERVER_ERROR",
            details=details
        )


class ServiceUnavailableError(AppException):
    """Service unavailable error - 503 Service Unavailable"""
    
    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Service unavailable: {service}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details or {"service": service}
        )
