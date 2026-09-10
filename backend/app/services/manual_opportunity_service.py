from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    LeadSource,
    ManualOpportunityCreationCommand,
    User,
    UserRole,
)
from app.services.customer_identity_service import (
    CustomerIdentityResolver,
    acquire_advisory_locks,
    comparable_phone,
    customer_identity_locks,
    normalize_email,
    normalize_optional_text,
)
from app.services.customer_profile_service import (
    CustomerProfileInput,
    create_customer_from_profile,
)
from app.services.errors import (
    ManualCustomerIdentityAmbiguousError,
    ManualCustomerIdentityDeletedError,
    ManualCustomerMatchExistsError,
    ManualOpportunityCommandConflictError,
    PermissionDeniedError,
)
from app.services.opportunity_service import OpportunityService


@dataclass(frozen=True, slots=True)
class ExistingCustomerInput:
    customer_id: int


@dataclass(frozen=True, slots=True)
class NewCustomerInput:
    name: str
    company: str | None
    phone: str | None
    email: str | None
    province: str | None


ManualCustomerInput = ExistingCustomerInput | NewCustomerInput


@dataclass(frozen=True, slots=True)
class ManualOpportunityCreationResult:
    opportunity_id: int
    created: bool


class ManualOpportunityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        command_id: UUID,
        customer_input: ManualCustomerInput,
        assigned_user_id: int | None,
        actor: User,
    ) -> ManualOpportunityCreationResult:
        normalized_customer = self._normalize_customer(customer_input)
        fingerprint = self._fingerprint(normalized_customer, assigned_user_id)
        command_lock = ("manual-opportunity-command", str(command_id))
        identity_locks = self._identity_locks(normalized_customer)

        with self._session.begin():
            acquire_advisory_locks(
                self._session,
                (command_lock, *identity_locks),
            )
            existing_command = self._session.scalar(
                select(ManualOpportunityCreationCommand).where(
                    ManualOpportunityCreationCommand.command_id == command_id
                )
            )
            if existing_command is not None:
                if (
                    existing_command.request_fingerprint != fingerprint
                    or existing_command.created_by_user_id != actor.id
                ):
                    raise ManualOpportunityCommandConflictError(
                        "Manual opportunity command was reused with different input"
                    )
                return ManualOpportunityCreationResult(
                    opportunity_id=existing_command.opportunity_id,
                    created=False,
                )

            if actor.role is UserRole.VENDEDOR and assigned_user_id is not None:
                raise PermissionDeniedError(
                    "Only supervisors can assign opportunity owners"
                )

            customer_id = self._resolve_customer_id(normalized_customer)
            opportunity = OpportunityService(
                self._session
            ).create_opportunity_in_transaction(
                customer_id=customer_id,
                source=LeadSource.REFERIDO,
                assigned_user_id=assigned_user_id,
                changed_by_user_id=actor.id,
            )
            self._session.add(
                ManualOpportunityCreationCommand(
                    command_id=command_id,
                    request_fingerprint=fingerprint,
                    opportunity_id=opportunity.id,
                    created_by_user_id=actor.id,
                )
            )
            self._session.flush()
            return ManualOpportunityCreationResult(
                opportunity_id=opportunity.id,
                created=True,
            )

    def _resolve_customer_id(self, customer_input: ManualCustomerInput) -> int:
        if isinstance(customer_input, ExistingCustomerInput):
            return customer_input.customer_id

        normalized_email = normalize_email(customer_input.email)
        phone_match_key = comparable_phone(customer_input.phone)
        resolution = CustomerIdentityResolver(self._session).resolve(
            normalized_email=normalized_email,
            phone_match_key=phone_match_key,
            lock_rows=True,
        )
        if resolution.has_deleted_matches:
            raise ManualCustomerIdentityDeletedError(
                "Manual customer identity matches a deleted customer"
            )
        if resolution.is_ambiguous:
            raise ManualCustomerIdentityAmbiguousError(
                "Manual customer identity matches multiple active customers"
            )
        if resolution.customer is not None:
            raise ManualCustomerMatchExistsError(resolution.customer)

        customer = create_customer_from_profile(
            self._session,
            CustomerProfileInput(
                name=customer_input.name,
                company=customer_input.company,
                email=normalized_email,
                phone=customer_input.phone,
                province=customer_input.province,
            ),
        )
        return customer.id

    @staticmethod
    def _normalize_customer(customer_input: ManualCustomerInput) -> ManualCustomerInput:
        if isinstance(customer_input, ExistingCustomerInput):
            return customer_input
        return NewCustomerInput(
            name=customer_input.name.strip(),
            company=normalize_optional_text(customer_input.company),
            phone=normalize_optional_text(customer_input.phone),
            email=normalize_email(customer_input.email),
            province=normalize_optional_text(customer_input.province),
        )

    @staticmethod
    def _identity_locks(
        customer_input: ManualCustomerInput,
    ) -> tuple[tuple[str, str], ...]:
        if isinstance(customer_input, ExistingCustomerInput):
            return ()
        return customer_identity_locks(
            normalize_email(customer_input.email),
            comparable_phone(customer_input.phone),
        )

    @staticmethod
    def _fingerprint(
        customer_input: ManualCustomerInput,
        assigned_user_id: int | None,
    ) -> str:
        if isinstance(customer_input, ExistingCustomerInput):
            canonical = (
                f"existing\x1f{customer_input.customer_id}\x1f{assigned_user_id}"
            )
        else:
            values = (
                "new",
                customer_input.name,
                customer_input.company or "",
                customer_input.phone or "",
                customer_input.email or "",
                customer_input.province or "",
                str(assigned_user_id) if assigned_user_id is not None else "",
            )
            canonical = "\x1f".join(values)
        return sha256(canonical.encode()).hexdigest()
