from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, LeadIntake, LeadSource
from app.services.errors import (
    CustomerIdentityConflictError,
    InvalidLeadIntakeError,
    LeadIntakeIdempotencyConflictError,
)
from app.services.opportunity_service import OpportunityService

MIN_MATCHABLE_PHONE_DIGITS = 7
_PHONE_REMOVALS = str.maketrans("", "", " \t\r\n\f\v-()")


@dataclass(frozen=True, slots=True)
class LeadIntakeInput:
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None
    message: str | None
    source: LeadSource
    external_submission_id: str


@dataclass(frozen=True, slots=True)
class LeadIntakeResult:
    intake_id: int
    customer_id: int
    opportunity_id: int
    created: bool


@dataclass(frozen=True, slots=True)
class _NormalizedLeadIntake:
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None
    message: str | None
    source: LeadSource
    external_submission_id: str
    comparable_phone: str | None


def normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized is not None else None


def comparable_phone(value: str | None) -> str | None:
    """Return a conservative match key, preserving '+' and country information."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    comparable = normalized.translate(_PHONE_REMOVALS)
    digit_count = sum(
        character.isascii() and character.isdigit() for character in comparable
    )
    if digit_count < MIN_MATCHABLE_PHONE_DIGITS:
        return None
    return comparable


def normalize_message(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalized or None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _advisory_lock_key(namespace: str, value: str) -> int:
    digest = sha256(f"{namespace}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


class LeadIntakeService:
    """Resolves a lead into Customer, Opportunity and immutable Intake atomically."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def intake(self, intake_input: LeadIntakeInput) -> LeadIntakeResult:
        normalized = self._normalize(intake_input)
        with self._session.begin():
            self._acquire_identity_locks(normalized)

            existing_intake = self._find_existing_intake(normalized)
            if existing_intake is not None:
                return self._replay_result(existing_intake, normalized)

            customer = self._resolve_customer(normalized)
            if customer is None:
                customer = self._create_customer(normalized)
            else:
                self._enrich_customer(customer, normalized)

            opportunity = OpportunityService(
                self._session
            ).create_opportunity_in_transaction(
                customer_id=customer.id,
                source=normalized.source,
                assigned_user_id=None,
                changed_by_user_id=None,
            )
            intake = LeadIntake(
                source=normalized.source,
                external_submission_id=normalized.external_submission_id,
                submitted_name=normalized.name,
                submitted_company=normalized.company,
                submitted_email=normalized.email,
                submitted_phone=normalized.phone,
                submitted_province=normalized.province,
                message=normalized.message,
                opportunity_id=opportunity.id,
            )
            self._session.add(intake)
            self._session.flush()

            return LeadIntakeResult(
                intake_id=intake.id,
                customer_id=customer.id,
                opportunity_id=opportunity.id,
                created=True,
            )

    def _normalize(self, intake_input: LeadIntakeInput) -> _NormalizedLeadIntake:
        name = intake_input.name.strip()
        external_submission_id = intake_input.external_submission_id.strip()
        if not name:
            raise InvalidLeadIntakeError("Lead name cannot be empty")
        if not external_submission_id:
            raise InvalidLeadIntakeError("External submission ID cannot be empty")
        if not isinstance(intake_input.source, LeadSource):
            raise InvalidLeadIntakeError("Lead source is invalid")

        phone = _normalize_optional_text(intake_input.phone)
        return _NormalizedLeadIntake(
            name=name,
            company=_normalize_optional_text(intake_input.company),
            email=normalize_email(intake_input.email),
            phone=phone,
            province=_normalize_optional_text(intake_input.province),
            message=normalize_message(intake_input.message),
            source=intake_input.source,
            external_submission_id=external_submission_id,
            comparable_phone=comparable_phone(phone),
        )

    def _acquire_identity_locks(self, intake: _NormalizedLeadIntake) -> None:
        lock_keys = {
            _advisory_lock_key(
                "intake",
                f"{intake.source.value}:{intake.external_submission_id}",
            )
        }
        if intake.email is not None:
            lock_keys.add(_advisory_lock_key("email", intake.email))
        if intake.comparable_phone is not None:
            lock_keys.add(_advisory_lock_key("phone", intake.comparable_phone))

        for lock_key in sorted(lock_keys):
            self._session.execute(select(func.pg_advisory_xact_lock(lock_key)))

    def _find_existing_intake(
        self,
        intake: _NormalizedLeadIntake,
    ) -> LeadIntake | None:
        return self._session.scalar(
            select(LeadIntake).where(
                LeadIntake.source == intake.source,
                LeadIntake.external_submission_id == intake.external_submission_id,
            )
        )

    def _replay_result(
        self,
        existing: LeadIntake,
        intake: _NormalizedLeadIntake,
    ) -> LeadIntakeResult:
        if not self._same_snapshot(existing, intake):
            raise LeadIntakeIdempotencyConflictError(
                "External submission ID was already used with different data"
            )
        return LeadIntakeResult(
            intake_id=existing.id,
            customer_id=existing.opportunity.customer_id,
            opportunity_id=existing.opportunity_id,
            created=False,
        )

    def _same_snapshot(
        self,
        existing: LeadIntake,
        intake: _NormalizedLeadIntake,
    ) -> bool:
        return (
            existing.submitted_name == intake.name
            and existing.submitted_company == intake.company
            and existing.submitted_email == intake.email
            and existing.submitted_phone == intake.phone
            and existing.submitted_province == intake.province
            and existing.message == intake.message
        )

    def _resolve_customer(self, intake: _NormalizedLeadIntake) -> Customer | None:
        email_matches = self._customers_matching_email(intake.email)
        phone_matches = self._customers_matching_phone(intake.comparable_phone)

        if len(email_matches) > 1 or len(phone_matches) > 1:
            raise CustomerIdentityConflictError(
                "Lead identity matches multiple active customers"
            )

        email_customer = email_matches[0] if email_matches else None
        phone_customer = phone_matches[0] if phone_matches else None
        if (
            email_customer is not None
            and phone_customer is not None
            and email_customer.id != phone_customer.id
        ):
            raise CustomerIdentityConflictError(
                "Lead email and phone identify different active customers"
            )
        return email_customer or phone_customer

    def _customers_matching_email(self, email: str | None) -> list[Customer]:
        if email is None:
            return []
        return list(
            self._session.scalars(
                select(Customer)
                .where(
                    Customer.deleted_at.is_(None),
                    func.lower(func.btrim(Customer.email)) == email,
                )
                .order_by(Customer.id)
                .with_for_update()
            ).all()
        )

    def _customers_matching_phone(
        self,
        phone_match_key: str | None,
    ) -> list[Customer]:
        if phone_match_key is None:
            return []
        return list(
            self._session.scalars(
                select(Customer)
                .where(
                    Customer.deleted_at.is_(None),
                    func.regexp_replace(
                        Customer.phone,
                        "[[:space:]()-]",
                        "",
                        "g",
                    )
                    == phone_match_key,
                )
                .order_by(Customer.id)
                .with_for_update()
            ).all()
        )

    def _create_customer(self, intake: _NormalizedLeadIntake) -> Customer:
        customer = Customer(
            name=intake.name,
            company=intake.company,
            email=intake.email,
            phone=intake.phone,
            province=intake.province,
            legendary_historical_override=False,
        )
        self._session.add(customer)
        self._session.flush()
        return customer

    def _enrich_customer(
        self,
        customer: Customer,
        intake: _NormalizedLeadIntake,
    ) -> None:
        changed = False
        if self._is_missing(customer.name):
            customer.name = intake.name
            changed = True
        if self._is_missing(customer.company) and intake.company is not None:
            customer.company = intake.company
            changed = True
        if self._is_missing(customer.email) and intake.email is not None:
            customer.email = intake.email
            changed = True
        if self._is_missing(customer.phone) and intake.phone is not None:
            customer.phone = intake.phone
            changed = True
        if self._is_missing(customer.province) and intake.province is not None:
            customer.province = intake.province
            changed = True
        if changed:
            customer.updated_at = datetime.now(UTC)
            self._session.flush()

    @staticmethod
    def _is_missing(value: str | None) -> bool:
        return value is None or not value.strip()
