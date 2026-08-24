from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="CONFIGURATION_ERROR", status_code=500, details=details)


class ValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400, details=details)


class NotFoundError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="NOT_FOUND", status_code=404, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None):
        super().__init__(message, code="UNAUTHORIZED", status_code=401, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None):
        super().__init__(message, code="FORBIDDEN", status_code=403, details=details)


class ConflictError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="CONFLICT", status_code=409, details=details)


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded", details: dict[str, Any] | None = None):
        super().__init__(message, code="RATE_LIMIT_EXCEEDED", status_code=429, details=details)


class ProviderError(AppException):
    def __init__(
        self,
        message: str,
        provider: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            code="PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider, **(details or {})},
        )


class AmbiguousLocationError(AppException):
    def __init__(self, candidates: list, message: str = "Ambiguous location"):
        super().__init__(
            message,
            code="AMBIGUOUS_LOCATION",
            status_code=400,
            details={"candidates": candidates},
        )


class NoRouteFoundError(AppException):
    def __init__(self, message: str = "No route found", details: dict[str, Any] | None = None):
        super().__init__(message, code="NO_ROUTE_FOUND", status_code=404, details=details)


class TicketError(AppException):
    def __init__(self, message: str, code: str = "TICKET_ERROR", status_code: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message, code=code, status_code=status_code, details=details)


class PaymentError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="PAYMENT_ERROR", status_code=402, details=details)


class AIProviderError(AppException):
    def __init__(self, message: str, request_stage: int, provider: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="AI_PROVIDER_ERROR",
            status_code=502,
            details={"request_stage": request_stage, "provider": provider, **(details or {})},
        )