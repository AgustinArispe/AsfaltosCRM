from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import DUMMY_PASSWORD_HASH, verify_password
from app.models import User
from app.services.errors import AuthenticationError


INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def authenticate(self, *, email: str, password: str) -> User:
        user = self._session.scalar(
            select(User).where(
                func.lower(func.btrim(User.email)) == email.strip().lower()
            )
        )
        if user is None:
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
        return user
