"""
Custom exception classes and global exception handlers.
"""
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class AppException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class TaskNotFoundException(AppException):
    """Exception raised when a task is not found."""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task with ID '{task_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id},
        )


class DatabaseConnectionError(AppException):
    """Exception raised when database connection fails."""
    
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DATABASE_ERROR",
        )


class ExternalAPIError(AppException):
    """Exception raised when external API call fails."""
    
    def __init__(
        self,
        message: str = "External API request failed",
        service: str = "unknown",
        original_error: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_API_ERROR",
            details={
                "service": service,
                "original_error": original_error,
            },
        )


class ExternalAPITimeoutError(AppException):
    """Exception raised when external API request times out."""
    
    def __init__(self, service: str = "unknown", timeout: int = 30):
        super().__init__(
            message=f"External API request to {service} timed out after {timeout} seconds",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="EXTERNAL_API_TIMEOUT",
            details={"service": service, "timeout": timeout},
        )


class ValidationError(AppException):
    """Exception raised for custom validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {},
        )


class ErrorResponseModel(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle application-specific exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponseModel(
                error=exc.message,
                error_code=exc.error_code,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors with detailed messages."""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponseModel(
                error="Validation failed",
                error_code="VALIDATION_ERROR",
                details={"errors": errors, "body": exc.body},
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        # In production, don't expose internal error details
        from app.core.config import settings
        
        error_message = str(exc) if settings.DEBUG else "An unexpected error occurred"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponseModel(
                error=error_message,
                error_code="INTERNAL_SERVER_ERROR",
            ).model_dump(),
        )
