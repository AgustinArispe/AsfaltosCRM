from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services import (
    AuthenticationError,
    ClosedOpportunityError,
    CustomerIdentityConflictError,
    DeletedCustomerError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    IdempotencyConflictError,
    InactiveProductError,
    InactiveUserError,
    IntakeAuthenticationError,
    InvalidCustomerImportError,
    InvalidLeadIntakeError,
    InvalidLossReasonError,
    InvalidQuoteProductsError,
    InvalidStateTransitionError,
    InvalidWhatsAppBroadcastError,
    InvalidWhatsAppCursorError,
    InvalidWhatsAppMessageError,
    LeadIntakeIdempotencyConflictError,
    MetricsTimelinePeriodTooLargeError,
    PermissionDeniedError,
    RevisionConflictError,
    StaleWriteConflictError,
    WhatsAppBroadcastConflictError,
    WhatsAppConversationResolutionError,
    WhatsAppFreeformWindowClosedError,
    WhatsAppIdempotencyConflictError,
    WhatsAppOpportunityAssociationError,
    WhatsAppReplyInProgressError,
)

DOMAIN_ERROR_STATUS: tuple[tuple[type[DomainError], int], ...] = (
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (IntakeAuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (PermissionDeniedError, status.HTTP_403_FORBIDDEN),
    (EntityNotFoundError, status.HTTP_404_NOT_FOUND),
    (DeletedCustomerError, status.HTTP_409_CONFLICT),
    (DuplicateEntityError, status.HTTP_409_CONFLICT),
    (CustomerIdentityConflictError, status.HTTP_409_CONFLICT),
    (LeadIntakeIdempotencyConflictError, status.HTTP_409_CONFLICT),
    (WhatsAppFreeformWindowClosedError, status.HTTP_409_CONFLICT),
    (WhatsAppConversationResolutionError, status.HTTP_409_CONFLICT),
    (WhatsAppIdempotencyConflictError, status.HTTP_409_CONFLICT),
    (WhatsAppOpportunityAssociationError, status.HTTP_409_CONFLICT),
    (WhatsAppReplyInProgressError, status.HTTP_409_CONFLICT),
    (WhatsAppBroadcastConflictError, status.HTTP_409_CONFLICT),
    (IdempotencyConflictError, status.HTTP_409_CONFLICT),
    (RevisionConflictError, status.HTTP_409_CONFLICT),
    (StaleWriteConflictError, status.HTTP_409_CONFLICT),
    (InactiveUserError, status.HTTP_409_CONFLICT),
    (InactiveProductError, status.HTTP_409_CONFLICT),
    (InvalidStateTransitionError, status.HTTP_409_CONFLICT),
    (ClosedOpportunityError, status.HTTP_409_CONFLICT),
    (InvalidQuoteProductsError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidLossReasonError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidLeadIntakeError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidWhatsAppCursorError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidWhatsAppMessageError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidWhatsAppBroadcastError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidCustomerImportError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (MetricsTimelinePeriodTooLargeError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


async def domain_error_handler(_: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, DomainError):
        raise TypeError("domain_error_handler requires a DomainError")
    response_status = status.HTTP_400_BAD_REQUEST
    for error_type, mapped_status in DOMAIN_ERROR_STATUS:
        if isinstance(error, error_type):
            response_status = mapped_status
            break
    headers = (
        {"WWW-Authenticate": "Bearer"}
        if isinstance(error, AuthenticationError)
        else None
    )
    if isinstance(error, MetricsTimelinePeriodTooLargeError):
        return JSONResponse(
            status_code=response_status,
            content={
                "detail": {
                    "code": error.code,
                    "granularity": error.granularity,
                    "requested_bucket_count": error.requested_bucket_count,
                    "maximum_bucket_count": error.maximum_bucket_count,
                }
            },
        )
    if isinstance(error, StaleWriteConflictError):
        return JSONResponse(
            status_code=response_status,
            content={
                "detail": {
                    "code": "STALE_WRITE",
                    "resource": error.resource,
                    "current_updated_at": error.current_updated_at.isoformat(),
                }
            },
        )
    return JSONResponse(
        status_code=response_status,
        content={"detail": str(error)},
        headers=headers,
    )
