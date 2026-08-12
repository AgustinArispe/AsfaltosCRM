from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    User,
    WhatsAppConsentDecision,
    WhatsAppConsentSource,
    WhatsAppMarketingConsentEvent,
)
from app.services.customer_identity_service import (
    acquire_advisory_locks,
    comparable_phone,
)
from app.services.errors import (
    EntityNotFoundError,
    InactiveUserError,
    InvalidWhatsAppBroadcastError,
    WhatsAppBroadcastConflictError,
)


@dataclass(frozen=True, slots=True)
class ConsentEventInput:
    client_event_id: UUID
    customer_id: int
    decision: WhatsAppConsentDecision
    source: WhatsAppConsentSource
    occurred_at: datetime
    effective_at: datetime | None
    evidence_reference: str | None
    recorded_by_user_id: int


@dataclass(frozen=True, slots=True)
class ConsentEventResult:
    event: WhatsAppMarketingConsentEvent
    current: WhatsAppMarketingConsentEvent
    created: bool


def consent_dispatch_lock(
    customer_id: int,
    normalized_phone: str,
) -> tuple[str, str]:
    return (
        "whatsapp-consent-dispatch",
        f"{customer_id}:{normalized_phone}",
    )


class WhatsAppConsentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        event_input: ConsentEventInput,
        *,
        now: datetime | None = None,
    ) -> ConsentEventResult:
        recorded_at = self._aware_utc(now or datetime.now(UTC))
        occurred_at = self._aware_utc(event_input.occurred_at)
        evidence = self._optional_text(event_input.evidence_reference)
        if occurred_at > recorded_at:
            raise InvalidWhatsAppBroadcastError("Consent occurrence cannot be future")
        if event_input.source is WhatsAppConsentSource.FAA_CRM:
            if event_input.effective_at is not None:
                raise InvalidWhatsAppBroadcastError(
                    "FAA CRM consent cannot supply effective_at"
                )
            effective_at = recorded_at
        else:
            if event_input.effective_at is None or evidence is None:
                raise InvalidWhatsAppBroadcastError(
                    "External FAA consent requires effective_at and evidence_reference"
                )
            effective_at = self._aware_utc(event_input.effective_at)
            if effective_at > recorded_at:
                raise InvalidWhatsAppBroadcastError(
                    "External FAA consent effective_at cannot be future"
                )

        with self._session.begin():
            discovered_customer = self._session.get(Customer, event_input.customer_id)
            if (
                discovered_customer is None
                or discovered_customer.deleted_at is not None
            ):
                raise EntityNotFoundError("Customer", event_input.customer_id)
            discovered_phone = comparable_phone(discovered_customer.phone)
            if discovered_phone is None:
                raise InvalidWhatsAppBroadcastError(
                    "Customer requires a valid phone for marketing consent"
                )
            acquire_advisory_locks(
                self._session,
                (
                    (
                        "whatsapp-consent-event",
                        str(event_input.client_event_id),
                    ),
                    consent_dispatch_lock(
                        discovered_customer.id,
                        discovered_phone,
                    ),
                ),
            )
            user = self._session.get(User, event_input.recorded_by_user_id)
            if user is None:
                raise EntityNotFoundError("User", event_input.recorded_by_user_id)
            if not user.is_active:
                raise InactiveUserError(user.id)
            customer = self._session.scalar(
                select(Customer)
                .where(Customer.id == event_input.customer_id)
                .with_for_update()
            )
            if customer is None or customer.deleted_at is not None:
                raise EntityNotFoundError("Customer", event_input.customer_id)
            normalized_phone = comparable_phone(customer.phone)
            if normalized_phone is None:
                raise InvalidWhatsAppBroadcastError(
                    "Customer requires a valid phone for marketing consent"
                )
            if normalized_phone != discovered_phone:
                raise WhatsAppBroadcastConflictError(
                    "Customer phone changed while consent was being recorded"
                )
            existing = self._session.scalar(
                select(WhatsAppMarketingConsentEvent)
                .where(
                    WhatsAppMarketingConsentEvent.client_event_id
                    == event_input.client_event_id
                )
                .with_for_update()
            )
            if existing is not None:
                self._assert_replay(
                    existing,
                    event_input,
                    normalized_phone=normalized_phone,
                    occurred_at=occurred_at,
                    evidence=evidence,
                )
                current = self._current_in_transaction(
                    existing.customer_id,
                    existing.normalized_phone,
                    now=recorded_at,
                )
                if current is None:
                    raise RuntimeError("Persisted consent has no current event")
                return ConsentEventResult(existing, current, False)
            event = WhatsAppMarketingConsentEvent(
                client_event_id=event_input.client_event_id,
                customer_id=customer.id,
                normalized_phone=normalized_phone,
                decision=event_input.decision,
                source=event_input.source,
                evidence_reference=evidence,
                occurred_at=occurred_at,
                effective_at=effective_at,
                recorded_at=recorded_at,
                recorded_by_user_id=user.id,
            )
            self._session.add(event)
            self._session.flush()
            current = self._current_in_transaction(
                customer.id,
                normalized_phone,
                now=recorded_at,
            )
            if current is None:
                raise RuntimeError("Created consent has no current event")
            return ConsentEventResult(event, current, True)

    def current(
        self,
        customer_id: int,
        normalized_phone: str,
        *,
        now: datetime,
    ) -> WhatsAppMarketingConsentEvent | None:
        return self._current_in_transaction(
            customer_id,
            normalized_phone,
            now=self._aware_utc(now),
        )

    def history(
        self,
        customer_id: int,
        *,
        limit: int,
        before_id: int | None,
    ) -> tuple[WhatsAppMarketingConsentEvent, ...]:
        statement = select(WhatsAppMarketingConsentEvent).where(
            WhatsAppMarketingConsentEvent.customer_id == customer_id
        )
        if before_id is not None:
            statement = statement.where(WhatsAppMarketingConsentEvent.id < before_id)
        return tuple(
            self._session.scalars(
                statement.order_by(WhatsAppMarketingConsentEvent.id.desc()).limit(limit)
            )
        )

    def _current_in_transaction(
        self,
        customer_id: int,
        normalized_phone: str,
        *,
        now: datetime,
    ) -> WhatsAppMarketingConsentEvent | None:
        return self._session.scalar(
            select(WhatsAppMarketingConsentEvent)
            .where(
                WhatsAppMarketingConsentEvent.customer_id == customer_id,
                WhatsAppMarketingConsentEvent.normalized_phone == normalized_phone,
                WhatsAppMarketingConsentEvent.effective_at <= now,
            )
            .order_by(
                WhatsAppMarketingConsentEvent.effective_at.desc(),
                WhatsAppMarketingConsentEvent.id.desc(),
            )
            .limit(1)
        )

    @staticmethod
    def _assert_replay(
        existing: WhatsAppMarketingConsentEvent,
        event_input: ConsentEventInput,
        *,
        normalized_phone: str,
        occurred_at: datetime,
        evidence: str | None,
    ) -> None:
        if not (
            existing.customer_id == event_input.customer_id
            and existing.normalized_phone == normalized_phone
            and existing.decision is event_input.decision
            and existing.source is event_input.source
            and existing.occurred_at == occurred_at
            and existing.evidence_reference == evidence
            and existing.recorded_by_user_id == event_input.recorded_by_user_id
            and (
                event_input.effective_at is None
                or existing.effective_at
                == WhatsAppConsentService._aware_utc(event_input.effective_at)
            )
        ):
            raise WhatsAppBroadcastConflictError(
                "Consent client_event_id was reused with different data"
            )

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
