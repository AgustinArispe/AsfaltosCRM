from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256

from phonenumbers import (
    NumberParseException,
    length_of_geographical_area_code,
    national_significant_number,
    parse,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Customer

MIN_MATCHABLE_PHONE_DIGITS = 7
_PHONE_REMOVALS = str.maketrans("", "", " \t\r\n\f\v-()")
_NUMERIC_PHONE = re.compile(r"\+?[0-9]+")
_ARGENTINE_LOCAL_MOBILE = re.compile(r"(?:(?:\+|00)?54)?15([0-9]{6,8})")


@dataclass(frozen=True, slots=True)
class _ArgentinePhone:
    national_number: str | None
    subscriber: str


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_email(value: str | None) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized.lower() if normalized is not None else None


def comparable_phone(value: str | None) -> str | None:
    """Remove formatting while preserving the original dialing prefixes."""
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


def _argentine_phone(phone_key: str) -> _ArgentinePhone | None:
    digits = phone_key.replace(".", "")
    if not _NUMERIC_PHONE.fullmatch(digits):
        return None
    if local := _ARGENTINE_LOCAL_MOBILE.fullmatch(digits):
        return _ArgentinePhone(national_number=None, subscriber=local[1])
    try:
        number = parse(digits, "AR")
    except NumberParseException:
        return None
    if number.country_code != 54:
        return None
    area_length = length_of_geographical_area_code(number)
    if not area_length:
        return None
    significant = national_significant_number(number)
    # Argentina's international mobile prefix is part of the significant
    # number used by libphonenumber, including its reported area length.
    national_number = (
        significant.removeprefix("9") if len(significant) == 11 else significant
    )
    return _ArgentinePhone(national_number, significant[area_length:])


def customer_phones_match(first: str, second: str) -> bool:
    """Compare two formatting-stripped phone keys for customer identity."""
    if first == second:
        return True
    first_number = _argentine_phone(first)
    second_number = _argentine_phone(second)
    if first_number is None or second_number is None:
        return False
    if first_number.national_number and second_number.national_number:
        return first_number.national_number == second_number.national_number
    return first_number.subscriber == second_number.subscriber


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
        argentine_phone = _argentine_phone(phone_match_key)
        if argentine_phone is None:
            identities.append(("phone", phone_match_key))
        else:
            # A local and a complete number can match, so serialize both.
            identities.append(("argentine-phone", argentine_phone.subscriber))
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
    """Resolve normalized identity signals across active and deleted customers."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve(
        self,
        *,
        normalized_email: str | None,
        phone_match_key: str | None,
        lock_rows: bool,
    ) -> CustomerIdentityResolution:
        filters: list[ColumnElement[bool]] = []
        if normalized_email is not None:
            filters.append(func.lower(func.btrim(Customer.email)) == normalized_email)
        if phone_match_key is not None:
            phone = _argentine_phone(phone_match_key)
            filters.append(
                func.regexp_replace(Customer.phone, "[^0-9]", "", "g").endswith(
                    phone.subscriber
                )
                if phone is not None
                else func.regexp_replace(Customer.phone, "[[:space:]()-]", "", "g")
                == phone_match_key
            )
        if not filters:
            return CustomerIdentityResolution((), ())
        statement = (
            select(Customer)
            .where(or_(*filters))
            .order_by(Customer.id)
            .execution_options(populate_existing=True)
        )
        matches = [
            customer
            for customer in self._session.scalars(statement)
            if _matches_customer(customer, normalized_email, phone_match_key)
        ]
        if lock_rows and matches:
            locked = (
                select(Customer)
                .where(Customer.id.in_([customer.id for customer in matches]))
                .order_by(Customer.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            matches = [
                customer
                for customer in self._session.scalars(locked)
                if _matches_customer(customer, normalized_email, phone_match_key)
            ]
        return CustomerIdentityResolution(
            active_matches=tuple(
                customer for customer in matches if customer.deleted_at is None
            ),
            deleted_match_ids=tuple(
                customer.id for customer in matches if customer.deleted_at is not None
            ),
        )


def _matches_customer(
    customer: Customer, normalized_email: str | None, phone_match_key: str | None
) -> bool:
    if (
        normalized_email is not None
        and normalize_email(customer.email) == normalized_email
    ):
        return True
    customer_phone = comparable_phone(customer.phone)
    return (
        phone_match_key is not None
        and customer_phone is not None
        and customer_phones_match(phone_match_key, customer_phone)
    )
