from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User, UserRole
from app.services.errors import DuplicateEntityError, EntityNotFoundError


USER_UPDATE_FIELDS = frozenset({"full_name", "email", "role", "is_active"})


class UserService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_users(self) -> list[User]:
        return list(self._session.scalars(select(User).order_by(User.full_name, User.id)))

    def get_user(self, user_id: int) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise EntityNotFoundError("User", user_id)
        return user

    def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password: str,
        role: UserRole,
    ) -> User:
        password_hash = hash_password(password)
        try:
            with self._session.begin():
                user = User(
                    full_name=full_name,
                    email=self._normalize_email(email),
                    password_hash=password_hash,
                    role=role,
                )
                self._session.add(user)
                self._session.flush()
        except IntegrityError as error:
            raise DuplicateEntityError("User", "email") from error
        return user

    def update_user(
        self,
        user_id: int,
        updates: dict[str, str | bool | UserRole | None],
    ) -> User:
        try:
            with self._session.begin():
                user = self._session.scalar(
                    select(User).where(User.id == user_id).with_for_update()
                )
                if user is None:
                    raise EntityNotFoundError("User", user_id)

                for field_name, value in updates.items():
                    if field_name not in USER_UPDATE_FIELDS:
                        continue
                    if field_name == "email" and isinstance(value, str):
                        value = self._normalize_email(value)
                    setattr(user, field_name, value)
                if updates:
                    user.updated_at = datetime.now(UTC)
                self._session.flush()
        except IntegrityError as error:
            raise DuplicateEntityError("User", "email") from error
        return user

    def change_password(self, user_id: int, password: str) -> User:
        password_hash = hash_password(password)
        with self._session.begin():
            user = self._session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if user is None:
                raise EntityNotFoundError("User", user_id)
            user.password_hash = password_hash
            user.updated_at = datetime.now(UTC)
            self._session.flush()
        return user

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
