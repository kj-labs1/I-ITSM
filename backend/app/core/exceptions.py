"""
Custom exception hierarchy for I-ITSM.

OOP Design: Demonstrates inheritance hierarchy where each exception type
represents a specific category of business or infrastructure error.
All exceptions inherit from a common IITSMException base, enabling
polymorphic exception handling at the API layer.

The hierarchy:

    IITSMException
    ├── ValidationError           (400)
    ├── AuthenticationError       (401)
    ├── AuthorizationError        (403)
    ├── NotFoundError             (404)
    │   ├── TechnicianNotFoundError
    │   └── IncidentNotFoundError
    ├── BusinessRuleError         (409)
    │   ├── SkillMismatchError
    │   ├── TechnicianUnavailableError
    │   ├── CapacityExceededError
    │   ├── NoEligibleTechnicianError
    │   ├── InvalidAssignmentError
    │   └── DuplicateAssignmentError
    ├── LLMProviderError          (502)
    │   ├── LLMTimeoutError
    │   └── LLMResponseValidationError
    └── DatabaseError             (500)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

# ── Base Exception ───────────────────────────────────────────────────────────


class IITSMException(Exception):
    """Base exception for the entire I-ITSM application.

    Every domain/infrastructure exception inherits from this class so the
    FastAPI exception handler can catch them uniformly and return a
    consistent error envelope.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


# ── Client Errors ────────────────────────────────────────────────────────────


class ValidationError(IITSMException):
    """Raised when request data fails domain validation (HTTP 400).

    Attributes:
        errors: A mapping of field names to lists of error messages,
                following the same shape as Pydantic validation errors.
    """

    def __init__(
        self,
        message: str = "Validation failed.",
        errors: dict[str, Any] | None = None,
        error_code: str = "VALIDATION_ERROR",
    ) -> None:
        self.errors = errors or {}
        super().__init__(message=message, error_code=error_code, status_code=400)


class AuthenticationError(IITSMException):
    """Raised when credentials are missing or invalid (HTTP 401)."""

    def __init__(
        self,
        message: str = "Authentication required.",
        error_code: str = "AUTHENTICATION_ERROR",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=401)


class AuthorizationError(IITSMException):
    """Raised when an authenticated user lacks permission (HTTP 403)."""

    def __init__(
        self,
        message: str = "Insufficient permissions.",
        error_code: str = "AUTHORIZATION_ERROR",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=403)


# ── Not-Found Errors ────────────────────────────────────────────────────────


class NotFoundError(IITSMException):
    """Raised when a requested resource does not exist (HTTP 404).

    Attributes:
        resource_type: Human-readable name of the resource (e.g. "Incident").
        resource_id: The identifier that was looked up.
    """

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: str | UUID | None = None,
        message: str | None = None,
        error_code: str = "NOT_FOUND",
    ) -> None:
        self.resource_type = resource_type
        self.resource_id = str(resource_id) if resource_id is not None else None
        if message is None:
            id_part = f" with id '{self.resource_id}'" if self.resource_id else ""
            message = f"{self.resource_type}{id_part} not found."
        super().__init__(message=message, error_code=error_code, status_code=404)


class TechnicianNotFoundError(NotFoundError):
    """A specific technician could not be found."""

    def __init__(self, resource_id: str | UUID | None = None, message: str | None = None) -> None:
        super().__init__(
            resource_type="Technician",
            resource_id=resource_id,
            message=message,
            error_code="TECHNICIAN_NOT_FOUND",
        )


class IncidentNotFoundError(NotFoundError):
    """A specific incident could not be found."""

    def __init__(self, resource_id: str | UUID | None = None, message: str | None = None) -> None:
        super().__init__(
            resource_type="Incident",
            resource_id=resource_id,
            message=message,
            error_code="INCIDENT_NOT_FOUND",
        )


# ── Business-Rule Errors ────────────────────────────────────────────────────


class BusinessRuleError(IITSMException):
    """Raised when a domain invariant or business rule is violated (HTTP 409).

    Subclasses represent specific rule violations in the assignment engine
    and related domain logic.
    """

    def __init__(
        self,
        message: str = "Business rule violation.",
        error_code: str = "BUSINESS_RULE_VIOLATION",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=409)


class SkillMismatchError(BusinessRuleError):
    """The technician does not possess the skills required by the incident."""

    def __init__(self, message: str = "Technician skills do not match incident requirements."):
        super().__init__(message=message, error_code="SKILL_MISMATCH")


class InvalidStatusTransitionError(BusinessRuleError):
    """
    Raised when an incident attempts an invalid lifecycle transition.

    HTTP Status: 409 Conflict
    Error Code: INVALID_STATUS_TRANSITION
    """

    def __init__(
        self,
        current_status: str,
        requested_status: str,
        incident_code: str | None = None,
    ) -> None:

        incident_reference = (
            f"Incident {incident_code}"
            if incident_code
            else "Incident"
        )

        message = (
            f"{incident_reference} cannot transition "
            f"from {current_status} to {requested_status}."
        )

        super().__init__(
            message=message,
            error_code="INVALID_STATUS_TRANSITION",
        )


class TechnicianUnavailableError(BusinessRuleError):
    """The technician is not in an AVAILABLE status."""

    def __init__(self, message: str = "Technician is not currently available."):
        super().__init__(message=message, error_code="TECHNICIAN_UNAVAILABLE")


class CapacityExceededError(BusinessRuleError):
    """Assigning the incident would exceed the technician's workload capacity."""

    def __init__(self, message: str = "Technician workload capacity would be exceeded."):
        super().__init__(message=message, error_code="CAPACITY_EXCEEDED")


class NoEligibleTechnicianError(BusinessRuleError):
    """No technician satisfies the eligibility criteria for the incident."""

    def __init__(self, message: str = "No eligible technician found for this incident."):
        super().__init__(message=message, error_code="NO_ELIGIBLE_TECHNICIAN")


class InvalidAssignmentError(BusinessRuleError):
    """The assignment request is structurally or semantically invalid."""

    def __init__(self, message: str = "Invalid assignment request."):
        super().__init__(message=message, error_code="INVALID_ASSIGNMENT")


class DuplicateAssignmentError(BusinessRuleError):
    """The incident is already assigned to the specified technician."""

    def __init__(self, message: str = "Incident is already assigned to this technician."):
        super().__init__(message=message, error_code="DUPLICATE_ASSIGNMENT")


# ── Infrastructure Errors ───────────────────────────────────────────────────


class LLMProviderError(IITSMException):
    """Raised when communication with the LLM provider fails (HTTP 502)."""

    def __init__(
        self,
        message: str = "LLM provider returned an error.",
        error_code: str = "LLM_PROVIDER_ERROR",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=502)


class LLMTimeoutError(LLMProviderError):
    """The LLM provider did not respond within the configured timeout."""

    def __init__(self, message: str = "LLM provider request timed out."):
        super().__init__(message=message, error_code="LLM_TIMEOUT")


class LLMResponseValidationError(LLMProviderError):
    """The LLM provider returned a response that could not be parsed or validated."""

    def __init__(self, message: str = "LLM response failed validation."):
        super().__init__(message=message, error_code="LLM_RESPONSE_VALIDATION")


class DatabaseError(IITSMException):
    """Raised when a database operation fails unexpectedly (HTTP 500)."""

    def __init__(self, message: str = "A database error occurred."):
        super().__init__(message=message, error_code="DATABASE_ERROR", status_code=500)


# ── Member 4 (SLA, Audit & Notifications) Errors ─────────────────────────────


class SLAPolicyNotFoundError(NotFoundError):
    """Requested SLA policy does not exist."""

    def __init__(self, resource_id: str | UUID | None = None, message: str | None = None) -> None:
        super().__init__(
            resource_type="SLAPolicy",
            resource_id=resource_id,
            message=message,
            error_code="SLA_POLICY_NOT_FOUND",
        )


class SLATrackingNotFoundError(NotFoundError):
    """SLA tracking record for the specified incident does not exist."""

    def __init__(self, resource_id: str | UUID | None = None, message: str | None = None) -> None:
        super().__init__(
            resource_type="IncidentSLATracking",
            resource_id=resource_id,
            message=message,
            error_code="SLA_TRACKING_NOT_FOUND",
        )


class NotificationNotFoundError(NotFoundError):
    """Requested notification record does not exist."""

    def __init__(self, resource_id: str | UUID | None = None, message: str | None = None) -> None:
        super().__init__(
            resource_type="Notification",
            resource_id=resource_id,
            message=message,
            error_code="NOTIFICATION_NOT_FOUND",
        )


class DuplicateSLAPolicyError(BusinessRuleError):
    """An SLA policy for the specified priority already exists."""

    def __init__(self, message: str = "An SLA policy for this priority already exists.") -> None:
        super().__init__(message=message, error_code="DUPLICATE_SLA_POLICY")
