from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import get_access_token_expire_minutes
from app.core.security import create_access_token
from app.schemas import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password",
)
def login(payload: LoginRequest, session: DatabaseSession) -> TokenResponse:
    user = AuthService(session).authenticate(
        email=payload.email,
        password=payload.password.get_secret_value(),
    )
    expires_in = get_access_token_expire_minutes() * 60
    return TokenResponse(
        access_token=create_access_token(
            user.id,
            auth_session_version=user.auth_session_version,
        ),
        expires_in=expires_in,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user",
)
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
