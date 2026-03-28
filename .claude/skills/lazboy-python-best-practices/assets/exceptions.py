"""
La-Z-Boy exception hierarchy template.

Copy this file into your service as `src/lazboy_<service>/exceptions.py`
and add service-specific exception types below the base classes.

Usage:
    from lazboy_myservice.exceptions import NotFoundError, ValidationError

    raise NotFoundError(f"Product {sku} not found")
    raise ValidationError("Price must be positive") from original_error
"""


class LazBoyError(Exception):
    """Base class for all La-Z-Boy application errors.

    Catch this to handle any application-level error generically.
    Prefer catching specific subclasses where possible.
    """


class ValidationError(LazBoyError):
    """Input failed business rule or schema validation.

    Raise this when user-supplied data doesn't meet requirements.
    HTTP handlers should map this to 422 Unprocessable Entity.
    """


class NotFoundError(LazBoyError):
    """A requested resource does not exist.

    HTTP handlers should map this to 404 Not Found.
    """


class AuthorizationError(LazBoyError):
    """The caller is not authorized to perform this action.

    HTTP handlers should map this to 403 Forbidden.
    """


class ConflictError(LazBoyError):
    """The operation conflicts with existing state (e.g., duplicate key).

    HTTP handlers should map this to 409 Conflict.
    """


class ExternalServiceError(LazBoyError):
    """A call to a downstream service or external API failed.

    Always chain the original exception:
        raise ExternalServiceError("...") from original_error

    HTTP handlers should map this to 502 Bad Gateway.
    """


class ConfigurationError(LazBoyError):
    """Application is misconfigured (missing env var, bad config value).

    Raise this at startup time — don't let misconfigured apps silently
    serve bad data or fail at runtime.
    """


# --- Add service-specific exceptions below ---
# Example:
#
# class ProductNotAvailableError(LazBoyError):
#     """Product exists but is not available for purchase."""
#
# class InventoryError(LazBoyError):
#     """Inventory operation failed (e.g., insufficient stock)."""
