"""Custom exceptions and global FastAPI exception handler."""

from fastapi import Request
from fastapi.responses import JSONResponse


class RegPulseException(Exception):
    """Base exception for all RegPulse application errors."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(message)


class InsufficientCreditsError(RegPulseException):
    http_status = 402
    error_code = "INSUFFICIENT_CREDITS"

    def __init__(self, message: str = "Insufficient credits to perform this action") -> None:
        super().__init__(message)


class PotentialInjectionError(RegPulseException):
    http_status = 400
    error_code = "POTENTIAL_INJECTION_DETECTED"

    def __init__(self, message: str = "Request blocked due to potential prompt injection") -> None:
        super().__init__(message)


class CircularNotFoundError(RegPulseException):
    http_status = 404
    error_code = "CIRCULAR_NOT_FOUND"

    def __init__(self, message: str = "Circular document not found") -> None:
        super().__init__(message)


class InvalidWorkEmailError(RegPulseException):
    http_status = 422
    error_code = "INVALID_WORK_EMAIL"

    def __init__(self, message: str = "A valid work email address is required") -> None:
        super().__init__(message)


class OTPRateLimitError(RegPulseException):
    http_status = 429
    error_code = "OTP_RATE_LIMIT"

    def __init__(self, message: str = "Too many OTP requests; try again later") -> None:
        super().__init__(message)


class OTPVerificationError(RegPulseException):
    http_status = 400
    error_code = "OTP_VERIFICATION_FAILED"

    def __init__(self, message: str = "Invalid or expired OTP") -> None:
        super().__init__(message)


class AuthenticationError(RegPulseException):
    http_status = 401
    error_code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


class AuthorizationError(RegPulseException):
    http_status = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission to perform this action") -> None:
        super().__init__(message)


class ServiceUnavailableError(RegPulseException):
    http_status = 503
    error_code = "SERVICE_UNAVAILABLE"

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Global exception handler — register on FastAPI app
# ---------------------------------------------------------------------------


async def regpulse_exception_handler(_request: Request, exc: RegPulseException) -> JSONResponse:
    """Return structured error JSON; never expose stack traces."""
    return JSONResponse(
        status_code=exc.http_status,
        content={"success": False, "error": exc.message, "code": exc.error_code},
    )


async def generic_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak internals."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
        },
    )
