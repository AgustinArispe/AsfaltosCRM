from fastapi import APIRouter, status

from app.api.dependencies import DatabaseSession, SupervisorUser
from app.schemas import PasswordUpdate, UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse], summary="List users")
def list_users(
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> list[UserResponse]:
    users = UserService(session).list_users()
    return [UserResponse.model_validate(user) for user in users]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(
    payload: UserCreate,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> UserResponse:
    user = UserService(session).create_user(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password.get_secret_value(),
        role=payload.role,
    )
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse, summary="Get user")
def get_user(
    user_id: int,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> UserResponse:
    user = UserService(session).get_user(user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, summary="Update user")
def update_user(
    user_id: int,
    payload: UserUpdate,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> UserResponse:
    user = UserService(session).update_user(
        user_id,
        payload.model_dump(exclude_unset=True),
    )
    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}/password",
    response_model=UserResponse,
    summary="Replace user password",
)
def change_password(
    user_id: int,
    payload: PasswordUpdate,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> UserResponse:
    user = UserService(session).change_password(
        user_id,
        payload.password.get_secret_value(),
    )
    return UserResponse.model_validate(user)
