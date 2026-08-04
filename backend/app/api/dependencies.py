from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models import User, UserRole
from app.services import AuthenticationError, PermissionDeniedError


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def get_db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@dataclass(frozen=True, slots=True)
class PaginationParams:
    page: int
    page_size: int


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    ] = DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


DatabaseSession = Annotated[Session, Depends(get_db_session)]
Pagination = Annotated[PaginationParams, Depends(get_pagination)]


bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="JWT access token returned by POST /api/auth/login",
    auto_error=False,
)


def get_current_user(
    session: DatabaseSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    if credentials is None:
        raise AuthenticationError("Could not validate credentials")
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as error:
        raise AuthenticationError("Could not validate credentials") from error

    with session.begin():
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Could not validate credentials")
        session.expunge(user)
    return user


def require_supervisor(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role is not UserRole.SUPERVISOR:
        raise PermissionDeniedError("Supervisor role is required")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
SupervisorUser = Annotated[User, Depends(require_supervisor)]
