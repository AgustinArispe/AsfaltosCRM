from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services import (
    AuthenticationError,
    ClosedOpportunityError,
    DeletedCustomerError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    InactiveProductError,
    InactiveUserError,
    InvalidLossReasonError,
    InvalidQuoteProductsError,
    InvalidStateTransitionError,
    PermissionDeniedError,
)


DOMAIN_ERROR_STATUS: tuple[tuple[type[DomainError], int], ...] = (
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (PermissionDeniedError, status.HTTP_403_FORBIDDEN),
    (EntityNotFoundError, status.HTTP_404_NOT_FOUND),
    (DeletedCustomerError, status.HTTP_409_CONFLICT),
    (DuplicateEntityError, status.HTTP_409_CONFLICT),
    (InactiveUserError, status.HTTP_409_CONFLICT),
    (InactiveProductError, status.HTTP_409_CONFLICT),
    (InvalidStateTransitionError, status.HTTP_409_CONFLICT),
    (ClosedOpportunityError, status.HTTP_409_CONFLICT),
    (InvalidQuoteProductsError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidLossReasonError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


async def domain_error_handler(_: Request, error: DomainError) -> JSONResponse:
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
    return JSONResponse(
        status_code=response_status,
        content={"detail": str(error)},
        headers=headers,
    )
