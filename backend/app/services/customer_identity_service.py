from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer

MIN_MATCHABLE_PHONE_DIGITS = 7
_PHONE_REMOVALS = str.maketrans("", "", " \t\r\n\f\v-()")


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_email(value: str | None) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized.lower() if normalized is not None else None


def comparable_phone(value: str | None) -> str | None:
    """Return a conservative match key, preserving '+' and country information."""
    normalized = normalize_optional_text(value)
    if normalized is None:
        return None
    comparable = normalized.translate(_PHONE_REMOVALS)
    digit_count = sum(
        character.isascii() and character.isdigit() for character in comparable
    )
    if digit_count < MIN_MATCHABLE_PHONE_DIGITS:
        return None
    return comparable


def advisory_lock_key(namespace: str, value: str) -> int:
    digest = sha256(f"{namespace}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def acquire_advisory_locks(
    session: Session,
    identities: tuple[tuple[str, str], ...],
) -> None:
    lock_keys = {advisory_lock_key(namespace, value) for namespace, value in identities}
    for lock_key in sorted(lock_keys):
        session.execute(select(func.pg_advisory_xact_lock(lock_key)))


def customer_identity_locks(
    normalized_email: str | None,
    phone_match_key: str | None,
) -> tuple[tuple[str, str], ...]:
    identities: list[tuple[str, str]] = []
    if normalized_email is not None:
        identities.append(("email", normalized_email))
    if phone_match_key is not None:
        identities.append(("phone", phone_match_key))
    return tuple(identities)


@dataclass(frozen=True, slots=True)
class CustomerIdentityResolution:
    active_matches: tuple[Customer, ...]
    deleted_match_ids: tuple[int, ...]

    @property
    def customer(self) -> Customer | None:
        return self.active_matches[0] if len(self.active_matches) == 1 else None

    @property
    def is_ambiguous(self) -> bool:
        return len(self.active_matches) > 1

    @property
    def has_deleted_matches(self) -> bool:
        return bool(self.deleted_match_ids)


class CustomerIdentityResolver:
    """Resolves exact active and deleted Customer identity signals."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve(
        self,
        *,
        normalized_email: str | None,
        phone_match_key: str | None,
        lock_rows: bool,
    ) -> CustomerIdentityResolution:
        matches_by_id: dict[int, Customer] = {}
        deleted_ids: set[int] = set()
        for customer in self._email_matches(normalized_email, lock_rows=lock_rows):
            self._classify(customer, matches_by_id, deleted_ids)
        for customer in self._phone_matches(phone_match_key, lock_rows=lock_rows):
            self._classify(customer, matches_by_id, deleted_ids)
        return CustomerIdentityResolution(
            active_matches=tuple(
                matches_by_id[customer_id] for customer_id in sorted(matches_by_id)
            ),
            deleted_match_ids=tuple(sorted(deleted_ids)),
        )

    def _email_matches(
        self,
        normalized_email: str | None,
        *,
        lock_rows: bool,
    ) -> list[Customer]:
        if normalized_email is None:
            return []
        statement = select(Customer).where(
            func.lower(func.btrim(Customer.email)) == normalized_email
        )
        if lock_rows:
            statement = statement.with_for_update()
        return list(self._session.scalars(statement.order_by(Customer.id)).all())

    def _phone_matches(
        self,
        phone_match_key: str | None,
        *,
        lock_rows: bool,
    ) -> list[Customer]:
        if phone_match_key is None:
            return []
        statement = select(Customer).where(
            func.regexp_replace(
                Customer.phone,
                "[[:space:]()-]",
                "",
                "g",
            )
            == phone_match_key
        )
        if lock_rows:
            statement = statement.with_for_update()
        return list(self._session.scalars(statement.order_by(Customer.id)).all())

    @staticmethod
    def _classify(
        customer: Customer,
        active_matches: dict[int, Customer],
        deleted_ids: set[int],
    ) -> None:
        if customer.deleted_at is None:
            active_matches[customer.id] = customer
        else:
            deleted_ids.add(customer.id)
