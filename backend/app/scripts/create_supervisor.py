import argparse
from getpass import getpass

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import User, UserRole
from app.services.user_service import UserService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the first CRM supervisor if the email does not exist."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    email = args.email.strip().lower()
    full_name = args.full_name.strip()
    if not email or not full_name:
        raise SystemExit("Email and full name cannot be blank")

    with SessionLocal() as session:
        with session.begin():
            existing_user = session.scalar(
                select(User).where(
                    func.lower(func.btrim(User.email)) == email
                )
            )
            if existing_user is not None:
                existing_role = existing_user.role
                existing_id = existing_user.id
            else:
                existing_role = None
                existing_id = None

        if existing_role is UserRole.SUPERVISOR:
            print(f"Supervisor already exists with id {existing_id}")
            return 0
        if existing_role is not None:
            raise SystemExit(
                "A non-supervisor user already exists with that email"
            )

        password = getpass("Password: ")
        confirmation = getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("Passwords do not match")
        if not 8 <= len(password) <= 128:
            raise SystemExit("Password must contain between 8 and 128 characters")

        user = UserService(session).create_user(
            full_name=full_name,
            email=email,
            password=password,
            role=UserRole.SUPERVISOR,
        )
        print(f"Supervisor created with id {user.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
