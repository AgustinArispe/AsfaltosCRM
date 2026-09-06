import sys
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.models import User, UserRole
from app.scripts import reset_user_password


def _password_inputs(values: list[str]) -> Iterator[str]:
    return iter(values)


def _create_user() -> tuple[int, str, str]:
    email = f"password-reset-{uuid4().hex}@faa.test"
    original_password = "original-cli-password"
    with SessionLocal.begin() as session:
        user = User(
            full_name="Password reset CLI user",
            email=email,
            password_hash=hash_password(original_password),
            role=UserRole.VENDEDOR,
        )
        session.add(user)
        session.flush()
        return user.id, email, original_password


def _delete_user(user_id: int) -> None:
    with SessionLocal.begin() as session:
        session.execute(delete(User).where(User.id == user_id))


def test_reset_user_password_cli_changes_existing_user_and_revokes_sessions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    user_id, email, original_password = _create_user()
    new_password = "new-cli-password"
    password_inputs = _password_inputs([new_password, new_password])
    monkeypatch.setattr(
        reset_user_password,
        "getpass",
        lambda _prompt: next(password_inputs),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["reset_user_password", "--email", f"  {email.upper()}  "],
    )

    try:
        assert reset_user_password.main() == 0
        output = capsys.readouterr().out
        with SessionLocal() as session:
            user = session.get(User, user_id)

        assert user is not None
        assert user.email == email
        assert user.role is UserRole.VENDEDOR
        assert user.auth_session_version == 2
        assert verify_password(new_password, user.password_hash)
        assert not verify_password(original_password, user.password_hash)
        assert output == f"Password reset for user with email {email}\n"
        assert new_password not in output
    finally:
        _delete_user(user_id)


@pytest.mark.parametrize(
    ("passwords", "message"),
    [
        (["valid-cli-password", "different-cli-password"], "Passwords do not match"),
        (["short", "short"], "Password must contain between 8 and 128 characters"),
    ],
)
def test_reset_user_password_cli_rejects_unsafe_password_input(
    monkeypatch: pytest.MonkeyPatch,
    passwords: list[str],
    message: str,
) -> None:
    user_id, email, original_password = _create_user()
    password_inputs = _password_inputs(passwords)
    monkeypatch.setattr(
        reset_user_password,
        "getpass",
        lambda _prompt: next(password_inputs),
    )
    monkeypatch.setattr(sys, "argv", ["reset_user_password", "--email", email])

    try:
        with pytest.raises(SystemExit, match=message):
            reset_user_password.main()
        with SessionLocal() as session:
            user = session.get(User, user_id)

        assert user is not None
        assert verify_password(original_password, user.password_hash)
        assert user.auth_session_version == 1
    finally:
        _delete_user(user_id)


def test_reset_user_password_cli_reports_missing_user_before_prompting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = f"missing-password-reset-{uuid4().hex}@faa.test"
    monkeypatch.setattr(sys, "argv", ["reset_user_password", "--email", email])

    def fail_if_prompted(_prompt: str) -> str:
        raise AssertionError("Password prompt must not be reached")

    monkeypatch.setattr(reset_user_password, "getpass", fail_if_prompted)

    with pytest.raises(SystemExit, match=f"User does not exist with email {email}"):
        reset_user_password.main()
