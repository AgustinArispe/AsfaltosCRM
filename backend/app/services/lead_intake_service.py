from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, LeadIntake, LeadSource
from app.services.customer_identity_service import (
    CustomerIdentityResolver,
    acquire_advisory_locks,
    customer_identity_locks,
    normalize_optional_text,
)
from app.services.customer_identity_service import (
    comparable_phone as comparable_phone,
)
from app.services.customer_identity_service import (
    normalize_email as normalize_email,
)
from app.services.customer_profile_service import (
    CustomerProfileInput,
    create_customer_from_profile,
    enrich_customer_missing_fields,
)
from app.services.errors import (
    CustomerIdentityConflictError,
    InvalidLeadIntakeError,
    LeadIntakeIdempotencyConflictError,
)
from app.services.opportunity_service import OpportunityService


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


def normalize_message(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalized or None


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

        phone = normalize_optional_text(intake_input.phone)
        return _NormalizedLeadIntake(
            name=name,
            company=normalize_optional_text(intake_input.company),
            email=normalize_email(intake_input.email),
            phone=phone,
            province=normalize_optional_text(intake_input.province),
            message=normalize_message(intake_input.message),
            source=intake_input.source,
            external_submission_id=external_submission_id,
            comparable_phone=comparable_phone(phone),
        )

    def _acquire_identity_locks(self, intake: _NormalizedLeadIntake) -> None:
        identities = (
            (
                "intake",
                f"{intake.source.value}:{intake.external_submission_id}",
            ),
            *customer_identity_locks(intake.email, intake.comparable_phone),
        )
        acquire_advisory_locks(self._session, identities)

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
        resolution = CustomerIdentityResolver(self._session).resolve(
            normalized_email=intake.email,
            phone_match_key=intake.comparable_phone,
            lock_rows=True,
        )
        if resolution.is_ambiguous:
            raise CustomerIdentityConflictError(
                "Lead identity matches multiple active customers"
            )
        return resolution.customer

    def _create_customer(self, intake: _NormalizedLeadIntake) -> Customer:
        return create_customer_from_profile(
            self._session,
            CustomerProfileInput(
                name=intake.name,
                company=intake.company,
                email=intake.email,
                phone=intake.phone,
                province=intake.province,
            ),
        )

    def _enrich_customer(
        self,
        customer: Customer,
        intake: _NormalizedLeadIntake,
    ) -> None:
        enrich_customer_missing_fields(
            self._session,
            customer,
            CustomerProfileInput(
                name=intake.name,
                company=intake.company,
                email=intake.email,
                phone=intake.phone,
                province=intake.province,
            ),
        )
