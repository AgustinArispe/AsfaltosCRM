from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Customer


@dataclass(frozen=True, slots=True)
class CustomerProfileInput:
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None


def create_customer_from_profile(
    session: Session,
    profile: CustomerProfileInput,
) -> Customer:
    customer = Customer(
        name=profile.name,
        company=profile.company,
        email=profile.email,
        phone=profile.phone,
        province=profile.province,
        legendary_historical_override=False,
        legendary_automatic=False,
    )
    session.add(customer)
    session.flush()
    return customer


def enrich_customer_missing_fields(
    session: Session,
    customer: Customer,
    profile: CustomerProfileInput,
) -> bool:
    changed = False
    for field_name, value in (
        ("name", profile.name),
        ("company", profile.company),
        ("email", profile.email),
        ("phone", profile.phone),
        ("province", profile.province),
    ):
        current_value = getattr(customer, field_name)
        if _is_missing(current_value) and value is not None:
            setattr(customer, field_name, value)
            changed = True
    if changed:
        customer.updated_at = datetime.now(UTC)
        session.flush()
    return changed


def customer_would_be_enriched(
    customer: Customer,
    profile: CustomerProfileInput,
) -> bool:
    return any(
        _is_missing(current_value) and incoming_value is not None
        for current_value, incoming_value in (
            (customer.name, profile.name),
            (customer.company, profile.company),
            (customer.email, profile.email),
            (customer.phone, profile.phone),
            (customer.province, profile.province),
        )
    )


def _is_missing(value: str | None) -> bool:
    return value is None or not value.strip()
