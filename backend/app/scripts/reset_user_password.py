import argparse
from getpass import getpass

from pydantic import TypeAdapter, ValidationError

from app.db.session import SessionLocal
from app.schemas.auth import PasswordInput
from app.services.errors import UserNotFoundByEmailError
from app.services.user_service import UserService

_password_input_adapter = TypeAdapter(PasswordInput)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reset the password for an existing CRM user."
    )
    parser.add_argument("--email", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    email = args.email.strip().lower()
    if not email:
        raise SystemExit("Email cannot be blank")

    with SessionLocal() as session:
        user_service = UserService(session)
        if user_service.get_user_by_email(email) is None:
            raise SystemExit(f"User does not exist with email {email}")
        session.rollback()

        password = getpass("New password: ")
        confirmation = getpass("Confirm new password: ")
        if password != confirmation:
            raise SystemExit("Passwords do not match")
        validated_password = _validate_password(password)

        try:
            user_service.change_password_by_email(email, validated_password)
        except UserNotFoundByEmailError as error:
            raise SystemExit(f"User does not exist with email {email}") from error

    print(f"Password reset for user with email {email}")
    return 0


def _validate_password(password: str) -> str:
    try:
        return _password_input_adapter.validate_python(password).get_secret_value()
    except ValidationError as error:
        raise SystemExit(
            "Password must contain between 8 and 128 characters"
        ) from error


if __name__ == "__main__":
    raise SystemExit(main())
