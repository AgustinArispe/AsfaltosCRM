from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, raiseload

from app.models import (
    Customer,
    WhatsAppAttachment,
    WhatsAppBroadcast,
    WhatsAppBroadcastAuditEvent,
    WhatsAppBroadcastAuditEventType,
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppBroadcastStatus,
    WhatsAppBroadcastTemplateParameter,
    WhatsAppConsentDecision,
    WhatsAppConversation,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppMessageOrigin,
    WhatsAppMessageType,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services.customer_identity_service import (
    acquire_advisory_locks,
    comparable_phone,
    customer_identity_locks,
)
from app.services.errors import (
    EntityNotFoundError,
    InvalidWhatsAppBroadcastError,
    WhatsAppBroadcastConflictError,
)
from app.services.whatsapp_broadcast_projection_service import (
    recompute_broadcast_recipient_projection,
)
from app.services.whatsapp_consent_service import (
    ConsentLookupKey,
    WhatsAppConsentService,
)
from app.services.whatsapp_message_service import (
    OutboundAttachmentInput,
    OutboundMessageInput,
    WhatsAppMessageService,
)
from app.services.whatsapp_projection_service import later_datetime
from app.whatsapp import (
    MediaStorage,
    MediaStorageError,
    ProviderTemplateSnapshot,
    StoredMedia,
    TemplateHeaderType,
    TemplateParameter,
    WhatsAppProvider,
)

VALIDATION_TTL = timedelta(minutes=10)
MAX_BROADCAST_PROCESS_BATCH_SIZE = 10


@dataclass(frozen=True, slots=True)
class BroadcastParameterInput:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class BroadcastCreateInput:
    client_generated_id: UUID
    label: str
    external_campaign_reference: str | None
    template_external_id: str
    parameters: tuple[BroadcastParameterInput, ...]
    header_media_ref: UUID | None
    created_by_user_id: int


@dataclass(frozen=True, slots=True)
class RecipientSelectionResult:
    broadcast_id: int
    version: int
    selected_count: int
    duplicate_customer_ids: tuple[int, ...]
    invalid_customer_ids: tuple[int, ...]
    missing_phone_customer_ids: tuple[int, ...]
    missing_consent_customer_ids: tuple[int, ...]
    replayed: bool


@dataclass(frozen=True, slots=True)
class BroadcastValidationResult:
    broadcast_id: int
    version: int
    valid: bool
    recipient_count: int
    issues: tuple[str, ...]
    validation_token: UUID | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class BroadcastProcessResult:
    broadcast_id: int
    claimed_count: int
    completed_count: int
    remaining_count: int
    replayed: bool


@dataclass(frozen=True, slots=True)
class BroadcastRetryResult:
    broadcast_id: int
    created_message_ids: tuple[int, ...]
    rejected_recipient_ids: tuple[int, ...]
    replayed: bool


@dataclass(frozen=True, slots=True)
class BroadcastStateCount:
    status: WhatsAppBroadcastRecipientStatus
    count: int


@dataclass(frozen=True, slots=True)
class BroadcastReasonCount:
    reason: str
    count: int


@dataclass(frozen=True, slots=True)
class BroadcastDeliverySummary:
    broadcast_id: int
    recipient_count: int
    message_attempt_count: int
    states: tuple[BroadcastStateCount, ...]
    reasons: tuple[BroadcastReasonCount, ...]
    accepted_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    first_completed_at: datetime | None
    last_completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class _ValidationSnapshot:
    issues: tuple[str, ...]
    consent_by_recipient: tuple[tuple[int, int], ...]
    digest: str


@dataclass(frozen=True, slots=True)
class _DispatchPlan:
    recipient_id: int
    conversation_id: int
    client_generated_id: UUID
    retry_of_message_id: int | None
    sent_by_user_id: int
    message_type: WhatsAppMessageType
    attachment: OutboundAttachmentInput | None
    template_name: str
    template_language: str
    parameters: tuple[TemplateParameter, ...]


@dataclass(frozen=True, slots=True)
class _ClaimCandidate:
    recipient_id: int
    customer_id: int
    normalized_phone: str
    initial_client_generated_id: UUID


class WhatsAppBroadcastService:
    def __init__(
        self,
        session: Session,
        provider: WhatsAppProvider,
        storage: MediaStorage,
        *,
        batch_size: int,
        claim_timeout: timedelta,
    ) -> None:
        if not 1 <= batch_size <= MAX_BROADCAST_PROCESS_BATCH_SIZE:
            raise ValueError(
                "Broadcast batch_size must be between 1 and "
                f"{MAX_BROADCAST_PROCESS_BATCH_SIZE}"
            )
        if claim_timeout <= timedelta(0):
            raise ValueError("Broadcast claim_timeout must be positive")
        self._session = session
        self._provider = provider
        self._storage = storage
        self._batch_size = batch_size
        self._claim_timeout = claim_timeout

    def list_templates(self) -> tuple[ProviderTemplateSnapshot, ...]:
        return tuple(
            template
            for template in self._provider.list_templates()
            if self._template_is_sendable(template)
        )

    def create(
        self,
        create_input: BroadcastCreateInput,
        *,
        now: datetime | None = None,
    ) -> tuple[WhatsAppBroadcast, bool]:
        created_at = self._aware_utc(now or datetime.now(UTC))
        label = self._required_text(create_input.label, "Broadcast label")
        external_reference = self._optional_text(
            create_input.external_campaign_reference
        )
        template = self._find_template(create_input.template_external_id)
        parameters = self._normalize_parameters(create_input.parameters)
        self._validate_parameters(template, parameters)
        media = self._header_media(template, create_input.header_media_ref)
        signature = self._template_signature(template)
        with self._session.begin():
            acquire_advisory_locks(
                self._session,
                (
                    (
                        "whatsapp-broadcast-create",
                        str(create_input.client_generated_id),
                    ),
                ),
            )
            existing = self._session.scalar(
                select(WhatsAppBroadcast)
                .where(
                    WhatsAppBroadcast.client_generated_id
                    == create_input.client_generated_id
                )
                .with_for_update()
            )
            if existing is not None:
                self._assert_create_replay(
                    existing,
                    create_input,
                    label=label,
                    external_reference=external_reference,
                    template=template,
                    parameters=parameters,
                    media=media,
                )
                return existing, False
            broadcast = WhatsAppBroadcast(
                client_generated_id=create_input.client_generated_id,
                label=label,
                external_campaign_reference=external_reference,
                template_external_id=template.external_id,
                template_name=template.name,
                template_language=template.language,
                template_category=template.category,
                template_provider_status=template.status,
                template_header_type=self._message_type(template.header_type),
                template_header_media_required=template.header_media_required,
                template_component_signature=signature,
                header_media_ref=media.media_ref if media is not None else None,
                header_media_storage_key=(
                    media.storage_key if media is not None else None
                ),
                header_media_mime_type=(media.mime_type if media is not None else None),
                header_media_filename=(media.filename if media is not None else None),
                header_media_size_bytes=(
                    media.size_bytes if media is not None else None
                ),
                header_media_sha256=media.sha256 if media is not None else None,
                created_by_user_id=create_input.created_by_user_id,
                created_at=created_at,
                updated_at=created_at,
            )
            self._session.add(broadcast)
            self._session.flush()
            for position, parameter in enumerate(parameters):
                self._session.add(
                    WhatsAppBroadcastTemplateParameter(
                        broadcast_id=broadcast.id,
                        position=position,
                        name=parameter.name,
                        value=parameter.value,
                    )
                )
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.CREATED,
                occurred_at=created_at,
                actor_user_id=create_input.created_by_user_id,
            )
            self._session.flush()
            return broadcast, True

    def replace_recipients(
        self,
        broadcast_id: int,
        *,
        command_id: UUID,
        customer_ids: tuple[int, ...],
        expected_version: int,
        actor_user_id: int,
        now: datetime | None = None,
    ) -> RecipientSelectionResult:
        changed_at = self._aware_utc(now or datetime.now(UTC))
        if not customer_ids:
            raise InvalidWhatsAppBroadcastError("At least one Customer is required")
        with self._session.begin():
            broadcast = self._broadcast_for_update(broadcast_id)
            if self._command_exists(broadcast.id, command_id):
                return RecipientSelectionResult(
                    broadcast.id,
                    broadcast.version,
                    len(broadcast.recipients),
                    (),
                    (),
                    (),
                    (),
                    True,
                )
            self._require_draft_version(broadcast, expected_version)
            customers = tuple(
                self._session.scalars(
                    select(Customer)
                    .where(Customer.id.in_(tuple(sorted(set(customer_ids)))))
                    .options(raiseload("*"))
                )
            )
            customers_by_id = {customer.id: customer for customer in customers}
            selected: list[tuple[Customer, str]] = []
            duplicate_ids: list[int] = []
            invalid_ids: list[int] = []
            missing_phone_ids: list[int] = []
            missing_consent_ids: list[int] = []
            seen_phones: set[str] = set()
            for customer_id in customer_ids:
                customer = customers_by_id.get(customer_id)
                if customer is None or customer.deleted_at is not None:
                    invalid_ids.append(customer_id)
                    continue
                phone = comparable_phone(customer.phone)
                if phone is None:
                    missing_phone_ids.append(customer_id)
                    continue
                if phone in seen_phones:
                    duplicate_ids.append(customer_id)
                    continue
                seen_phones.add(phone)
                selected.append((customer, phone))
            consent_by_key = WhatsAppConsentService(self._session).current_many(
                tuple(
                    ConsentLookupKey(customer.id, phone) for customer, phone in selected
                ),
                now=changed_at,
            )
            for customer, phone in selected:
                current = consent_by_key.get(ConsentLookupKey(customer.id, phone))
                if (
                    current is None
                    or current.decision is not WhatsAppConsentDecision.OPT_IN
                ):
                    missing_consent_ids.append(customer.id)
            self._session.execute(
                delete(WhatsAppBroadcastRecipient).where(
                    WhatsAppBroadcastRecipient.broadcast_id == broadcast.id
                )
            )
            for customer, phone in selected:
                self._session.add(
                    WhatsAppBroadcastRecipient(
                        broadcast_id=broadcast.id,
                        customer_id=customer.id,
                        customer_display_name=customer.name,
                        normalized_phone=phone,
                        status=WhatsAppBroadcastRecipientStatus.DRAFT,
                        created_at=changed_at,
                        updated_at=changed_at,
                    )
                )
            broadcast.version += 1
            broadcast.validation_token = None
            broadcast.validation_digest = None
            broadcast.validation_expires_at = None
            broadcast.updated_at = changed_at
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.RECIPIENTS_REPLACED,
                occurred_at=changed_at,
                actor_user_id=actor_user_id,
                command_id=command_id,
                affected_count=len(selected),
            )
            self._session.flush()
            return RecipientSelectionResult(
                broadcast.id,
                broadcast.version,
                len(selected),
                tuple(duplicate_ids),
                tuple(invalid_ids),
                tuple(missing_phone_ids),
                tuple(missing_consent_ids),
                False,
            )

    def validate(
        self,
        broadcast_id: int,
        *,
        expected_version: int,
        actor_user_id: int,
        now: datetime | None = None,
    ) -> BroadcastValidationResult:
        validated_at = self._aware_utc(now or datetime.now(UTC))
        templates = self._provider.list_templates()
        with self._session.begin():
            broadcast = self._broadcast_for_update(broadcast_id)
            self._require_draft_version(broadcast, expected_version)
            recipients = self._validation_recipients(broadcast.id, for_update=False)
            parameters = self._validation_parameters(broadcast.id)
            snapshot = self._validation_snapshot(
                broadcast,
                recipients=recipients,
                parameters=parameters,
                templates=templates,
                now=validated_at,
            )
            token = uuid4() if not snapshot.issues else None
            expires_at = validated_at + VALIDATION_TTL if token is not None else None
            broadcast.validation_token = token
            broadcast.validation_digest = snapshot.digest if token is not None else None
            broadcast.validation_expires_at = expires_at
            broadcast.validated_at = validated_at
            broadcast.updated_at = validated_at
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.VALIDATED,
                occurred_at=validated_at,
                actor_user_id=actor_user_id,
                affected_count=len(recipients),
                reason_code="VALID" if token is not None else "INVALID",
            )
            return BroadcastValidationResult(
                broadcast.id,
                broadcast.version,
                token is not None,
                len(recipients),
                snapshot.issues,
                token,
                expires_at,
            )

    def confirm(
        self,
        broadcast_id: int,
        *,
        command_id: UUID,
        expected_version: int,
        validation_token: UUID,
        actor_user_id: int,
        now: datetime | None = None,
    ) -> WhatsAppBroadcast:
        confirmed_at = self._aware_utc(now or datetime.now(UTC))
        templates = self._provider.list_templates()
        with self._session.begin():
            broadcast = self._broadcast_for_update(broadcast_id)
            if self._command_exists(broadcast.id, command_id):
                return broadcast
            self._require_draft_version(broadcast, expected_version)
            if (
                broadcast.validation_token != validation_token
                or broadcast.validation_expires_at is None
                or broadcast.validation_expires_at < confirmed_at
            ):
                raise WhatsAppBroadcastConflictError(
                    "Broadcast validation token is missing, stale, or invalid"
                )
            recipients = self._validation_recipients(broadcast.id, for_update=True)
            parameters = self._validation_parameters(broadcast.id)
            snapshot = self._validation_snapshot(
                broadcast,
                recipients=recipients,
                parameters=parameters,
                templates=templates,
                now=confirmed_at,
            )
            if snapshot.issues or snapshot.digest != broadcast.validation_digest:
                raise WhatsAppBroadcastConflictError(
                    "Broadcast inputs or eligibility changed after validation"
                )
            consent_ids = dict(snapshot.consent_by_recipient)
            for recipient in recipients:
                recipient.consent_event_id = consent_ids[recipient.id]
                recipient.status = WhatsAppBroadcastRecipientStatus.READY
                recipient.confirmed_at = confirmed_at
                recipient.updated_at = confirmed_at
            broadcast.status = WhatsAppBroadcastStatus.CONFIRMED
            broadcast.confirmed_by_user_id = actor_user_id
            broadcast.confirmed_at = confirmed_at
            broadcast.validation_token = None
            broadcast.updated_at = confirmed_at
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.CONFIRMED,
                occurred_at=confirmed_at,
                actor_user_id=actor_user_id,
                command_id=command_id,
                affected_count=len(recipients),
            )
            self._session.flush()
            return broadcast

    def start(
        self,
        broadcast_id: int,
        *,
        command_id: UUID,
        actor_user_id: int,
        now: datetime | None = None,
    ) -> WhatsAppBroadcast:
        started_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            broadcast = self._broadcast_for_update(broadcast_id)
            if self._command_exists(broadcast.id, command_id):
                return broadcast
            if broadcast.status is not WhatsAppBroadcastStatus.CONFIRMED:
                raise WhatsAppBroadcastConflictError(
                    "Only a confirmed Broadcast can start"
                )
            broadcast.status = WhatsAppBroadcastStatus.PROCESSING
            broadcast.started_by_user_id = actor_user_id
            broadcast.started_at = started_at
            broadcast.updated_at = started_at
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.STARTED,
                occurred_at=started_at,
                actor_user_id=actor_user_id,
                command_id=command_id,
            )
            return broadcast

    def process_batch(
        self,
        broadcast_id: int,
        *,
        command_id: UUID,
        actor_user_id: int | None,
        now: datetime | None = None,
    ) -> BroadcastProcessResult:
        processed_at = self._aware_utc(now or datetime.now(UTC))
        templates = self._provider.list_templates()
        self._recover_stale_claims_transaction(
            broadcast_id,
            now=processed_at,
        )
        candidates = self._claim_candidates(broadcast_id)
        with self._session.begin():
            advisory_identities: list[tuple[str, str]] = [
                (
                    "whatsapp-broadcast-command",
                    f"{broadcast_id}:{command_id}",
                )
            ]
            for candidate in candidates:
                advisory_identities.extend(
                    customer_identity_locks(None, candidate.normalized_phone)
                )
                advisory_identities.append(
                    (
                        "whatsapp-outbound-message",
                        str(candidate.initial_client_generated_id),
                    )
                )
            acquire_advisory_locks(
                self._session,
                tuple(advisory_identities),
            )
            broadcast = self._session.get(WhatsAppBroadcast, broadcast_id)
            if broadcast is None:
                raise EntityNotFoundError("WhatsAppBroadcast", broadcast_id)
            if self._command_exists(broadcast.id, command_id):
                return self._process_result(broadcast, 0, True)
            if broadcast.status is not WhatsAppBroadcastStatus.PROCESSING:
                raise WhatsAppBroadcastConflictError(
                    "Broadcast must be processing before claiming recipients"
                )
            candidate_by_id = {
                candidate.recipient_id: candidate for candidate in candidates
            }
            customer_ids = sorted({candidate.customer_id for candidate in candidates})
            if customer_ids:
                tuple(
                    self._session.scalars(
                        select(Customer)
                        .where(Customer.id.in_(customer_ids))
                        .order_by(Customer.id)
                        .with_for_update()
                    )
                )
            recipients = tuple(
                self._session.scalars(
                    select(WhatsAppBroadcastRecipient)
                    .where(
                        WhatsAppBroadcastRecipient.broadcast_id == broadcast.id,
                        WhatsAppBroadcastRecipient.id.in_(candidate_by_id),
                        WhatsAppBroadcastRecipient.status
                        == WhatsAppBroadcastRecipientStatus.READY,
                    )
                    .order_by(WhatsAppBroadcastRecipient.id)
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            for recipient in recipients:
                conversation = self._conversation_for_recipient(recipient)
                recipient.conversation_id = conversation.id
            latest_by_recipient = self._latest_messages_for_recipients_locked(
                tuple(recipient.id for recipient in recipients)
            )
            claimed_recipients: list[WhatsAppBroadcastRecipient] = []
            for recipient in recipients:
                existing = latest_by_recipient.get(recipient.id)
                if existing is None:
                    candidate = candidate_by_id[recipient.id]
                    self._pending_broadcast_message(
                        broadcast,
                        recipient,
                        previous=None,
                        actor_user_id=self._broadcast_sender(broadcast),
                        client_generated_id=candidate.initial_client_generated_id,
                    )
                elif existing.dispatch_state is WhatsAppDispatchState.PENDING:
                    pass
                else:
                    self._block(recipient, "ATTEMPT_ALREADY_EXISTS", now=processed_at)
                    continue
                recipient.status = WhatsAppBroadcastRecipientStatus.IN_PROGRESS
                recipient.claim_token = command_id
                recipient.claimed_at = processed_at
                recipient.updated_at = processed_at
                recompute_broadcast_recipient_projection(
                    self._session,
                    recipient,
                    now=processed_at,
                )
                claimed_recipients.append(recipient)
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.PROCESSED,
                occurred_at=processed_at,
                actor_user_id=actor_user_id,
                command_id=command_id,
                affected_count=len(claimed_recipients),
            )
            recipient_ids = tuple(recipient.id for recipient in claimed_recipients)
        completed_count = 0
        for recipient_id in recipient_ids:
            plan = self._prepare_dispatch(
                recipient_id,
                templates=templates,
                now=processed_at,
            )
            if plan is None:
                completed_count += 1
                continue
            WhatsAppMessageService(self._session, self._provider).send(
                OutboundMessageInput(
                    conversation_id=plan.conversation_id,
                    client_generated_id=plan.client_generated_id,
                    sent_by_user_id=plan.sent_by_user_id,
                    message_type=plan.message_type,
                    body=None,
                    attachment=plan.attachment,
                    retry_of_message_id=plan.retry_of_message_id,
                    origin=WhatsAppMessageOrigin.BROADCAST,
                    broadcast_recipient_id=plan.recipient_id,
                    template_name=plan.template_name,
                    template_language=plan.template_language,
                    template_parameters=plan.parameters,
                ),
                now=processed_at,
            )
            completed_count += 1
        with self._session.begin():
            broadcast = self._broadcast_for_update(broadcast_id)
            self._complete_if_idle(broadcast, now=processed_at)
            return self._process_result(
                broadcast,
                len(recipient_ids),
                False,
                completed_count=completed_count,
            )

    def retry_failed(
        self,
        broadcast_id: int,
        *,
        command_id: UUID,
        recipient_ids: tuple[int, ...],
        actor_user_id: int,
        now: datetime | None = None,
    ) -> BroadcastRetryResult:
        retried_at = self._aware_utc(now or datetime.now(UTC))
        if not recipient_ids:
            raise InvalidWhatsAppBroadcastError("Retry requires recipient IDs")
        templates = self._provider.list_templates()
        candidates = self._retry_candidates(broadcast_id, recipient_ids)
        created_ids: list[int] = []
        rejected_ids: list[int] = []
        with self._session.begin():
            advisory_identities: list[tuple[str, str]] = [
                (
                    "whatsapp-broadcast-command",
                    f"{broadcast_id}:{command_id}",
                )
            ]
            for candidate in candidates:
                advisory_identities.append(
                    (
                        "whatsapp-consent-dispatch",
                        f"{candidate.customer_id}:{candidate.normalized_phone}",
                    )
                )
                advisory_identities.append(
                    (
                        "whatsapp-outbound-message",
                        str(candidate.initial_client_generated_id),
                    )
                )
            acquire_advisory_locks(
                self._session,
                tuple(advisory_identities),
            )
            candidate_by_id = {
                candidate.recipient_id: candidate for candidate in candidates
            }
            customer_ids = sorted({candidate.customer_id for candidate in candidates})
            if customer_ids:
                tuple(
                    self._session.scalars(
                        select(Customer)
                        .where(Customer.id.in_(customer_ids))
                        .order_by(Customer.id)
                        .with_for_update()
                    )
                )
            broadcast = self._broadcast_for_update(broadcast_id)
            if self._command_exists(broadcast.id, command_id):
                return BroadcastRetryResult(broadcast.id, (), (), True)
            template = self._template_for_broadcast(broadcast, templates)
            if template is None:
                raise WhatsAppBroadcastConflictError(
                    "Broadcast template is no longer approved or unchanged"
                )
            locked_recipients = tuple(
                self._session.scalars(
                    select(WhatsAppBroadcastRecipient)
                    .where(
                        WhatsAppBroadcastRecipient.id.in_(candidate_by_id),
                        WhatsAppBroadcastRecipient.broadcast_id == broadcast.id,
                    )
                    .order_by(WhatsAppBroadcastRecipient.id)
                    .with_for_update()
                )
            )
            recipient_by_id = {
                recipient.id: recipient for recipient in locked_recipients
            }
            conversation_ids = sorted(
                {
                    recipient.conversation_id
                    for recipient in locked_recipients
                    if recipient.conversation_id is not None
                }
            )
            if conversation_ids:
                tuple(
                    self._session.scalars(
                        select(WhatsAppConversation)
                        .where(WhatsAppConversation.id.in_(conversation_ids))
                        .order_by(WhatsAppConversation.id)
                        .with_for_update()
                    )
                )
            latest_by_recipient = self._latest_messages_for_recipients_locked(
                tuple(recipient.id for recipient in locked_recipients)
            )
            for recipient_id in recipient_ids:
                recipient = recipient_by_id.get(recipient_id)
                eligibility_at = datetime.now(UTC)
                if (
                    recipient is None
                    or recipient.status is not WhatsAppBroadcastRecipientStatus.FAILED
                    or not self._recipient_is_eligible(
                        recipient,
                        now=eligibility_at,
                    )
                ):
                    rejected_ids.append(recipient_id)
                    continue
                previous = latest_by_recipient[recipient.id]
                if previous is None or not self._message_failed(previous):
                    rejected_ids.append(recipient_id)
                    continue
                candidate = candidate_by_id[recipient.id]
                message = self._pending_broadcast_message(
                    broadcast,
                    recipient,
                    previous=previous,
                    actor_user_id=actor_user_id,
                    client_generated_id=candidate.initial_client_generated_id,
                )
                created_ids.append(message.id)
                recipient.reason_code = None
                recipient.claim_token = None
                recipient.claimed_at = None
                recompute_broadcast_recipient_projection(
                    self._session,
                    recipient,
                    now=retried_at,
                )
            if created_ids:
                broadcast.status = WhatsAppBroadcastStatus.PROCESSING
                broadcast.updated_at = retried_at
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.RETRY_AUTHORIZED,
                occurred_at=retried_at,
                actor_user_id=actor_user_id,
                command_id=command_id,
                affected_count=len(created_ids),
            )
            return BroadcastRetryResult(
                broadcast.id,
                tuple(created_ids),
                tuple(rejected_ids),
                False,
            )

    def get(self, broadcast_id: int) -> WhatsAppBroadcast:
        broadcast = self._session.get(WhatsAppBroadcast, broadcast_id)
        if broadcast is None:
            raise EntityNotFoundError("WhatsAppBroadcast", broadcast_id)
        return broadcast

    def list(
        self,
        *,
        status: WhatsAppBroadcastStatus | None,
        limit: int,
        before_id: int | None,
    ) -> tuple[WhatsAppBroadcast, ...]:
        statement = select(WhatsAppBroadcast)
        if status is not None:
            statement = statement.where(WhatsAppBroadcast.status == status)
        if before_id is not None:
            statement = statement.where(WhatsAppBroadcast.id < before_id)
        return tuple(
            self._session.scalars(
                statement.order_by(WhatsAppBroadcast.id.desc()).limit(limit)
            )
        )

    def delivery_summary(self, broadcast_id: int) -> BroadcastDeliverySummary:
        broadcast = self.get(broadcast_id)
        rows = self._session.execute(
            select(
                WhatsAppBroadcastRecipient.status,
                func.count(WhatsAppBroadcastRecipient.id),
            )
            .where(WhatsAppBroadcastRecipient.broadcast_id == broadcast_id)
            .group_by(WhatsAppBroadcastRecipient.status)
        ).all()
        states = tuple(
            BroadcastStateCount(status=row[0], count=row[1])
            for row in sorted(rows, key=lambda item: item[0].value)
        )
        recipient_count = sum(item.count for item in states)
        attempts = self._session.scalar(
            select(func.count(WhatsAppMessage.id))
            .join(
                WhatsAppBroadcastRecipient,
                WhatsAppBroadcastRecipient.id == WhatsAppMessage.broadcast_recipient_id,
            )
            .where(WhatsAppBroadcastRecipient.broadcast_id == broadcast_id)
        )
        reason = func.coalesce(
            WhatsAppBroadcastRecipient.reason_code,
            WhatsAppBroadcastRecipient.safe_error_code,
            "UNSPECIFIED",
        )
        reason_rows = self._session.execute(
            select(reason, func.count(WhatsAppBroadcastRecipient.id))
            .where(
                WhatsAppBroadcastRecipient.broadcast_id == broadcast_id,
                WhatsAppBroadcastRecipient.status.in_(
                    {
                        WhatsAppBroadcastRecipientStatus.FAILED,
                        WhatsAppBroadcastRecipientStatus.UNKNOWN,
                        WhatsAppBroadcastRecipientStatus.BLOCKED,
                    }
                ),
            )
            .group_by(reason)
            .order_by(reason)
        ).all()
        timestamps = self._session.execute(
            select(
                func.max(WhatsAppBroadcastRecipient.accepted_at),
                func.max(WhatsAppBroadcastRecipient.sent_at),
                func.max(WhatsAppBroadcastRecipient.delivered_at),
                func.max(WhatsAppBroadcastRecipient.read_at),
                func.max(WhatsAppBroadcastRecipient.failed_at),
            ).where(WhatsAppBroadcastRecipient.broadcast_id == broadcast_id)
        ).one()
        return BroadcastDeliverySummary(
            broadcast_id,
            recipient_count,
            attempts or 0,
            states,
            tuple(BroadcastReasonCount(row[0], row[1]) for row in reason_rows),
            timestamps[0],
            timestamps[1],
            timestamps[2],
            timestamps[3],
            timestamps[4],
            broadcast.first_completed_at,
            broadcast.last_completed_at,
        )

    def _claim_candidates(
        self,
        broadcast_id: int,
    ) -> tuple[_ClaimCandidate, ...]:
        with self._session.begin():
            rows = self._session.execute(
                select(
                    WhatsAppBroadcastRecipient.id,
                    WhatsAppBroadcastRecipient.customer_id,
                    WhatsAppBroadcastRecipient.normalized_phone,
                )
                .where(
                    WhatsAppBroadcastRecipient.broadcast_id == broadcast_id,
                    WhatsAppBroadcastRecipient.status
                    == WhatsAppBroadcastRecipientStatus.READY,
                )
                .order_by(WhatsAppBroadcastRecipient.id)
                .limit(self._batch_size * 2)
            ).all()
            return tuple(
                _ClaimCandidate(
                    recipient_id=row.id,
                    customer_id=row.customer_id,
                    normalized_phone=row.normalized_phone,
                    initial_client_generated_id=uuid4(),
                )
                for row in rows
            )

    def _retry_candidates(
        self,
        broadcast_id: int,
        recipient_ids: tuple[int, ...],
    ) -> tuple[_ClaimCandidate, ...]:
        with self._session.begin():
            rows = self._session.execute(
                select(
                    WhatsAppBroadcastRecipient.id,
                    WhatsAppBroadcastRecipient.customer_id,
                    WhatsAppBroadcastRecipient.normalized_phone,
                )
                .where(
                    WhatsAppBroadcastRecipient.broadcast_id == broadcast_id,
                    WhatsAppBroadcastRecipient.id.in_(set(recipient_ids)),
                )
                .order_by(WhatsAppBroadcastRecipient.id)
            ).all()
            return tuple(
                _ClaimCandidate(
                    recipient_id=row.id,
                    customer_id=row.customer_id,
                    normalized_phone=row.normalized_phone,
                    initial_client_generated_id=uuid4(),
                )
                for row in rows
            )

    def _recover_stale_claims_transaction(
        self,
        broadcast_id: int,
        *,
        now: datetime,
    ) -> None:
        with self._session.begin():
            broadcast = self._session.get(WhatsAppBroadcast, broadcast_id)
            if broadcast is None:
                raise EntityNotFoundError("WhatsAppBroadcast", broadcast_id)
            if broadcast.status is WhatsAppBroadcastStatus.PROCESSING:
                self._recover_stale_claims(broadcast, now=now)

    def _prepare_dispatch(
        self,
        recipient_id: int,
        *,
        templates: tuple[ProviderTemplateSnapshot, ...],
        now: datetime,
    ) -> _DispatchPlan | None:
        with self._session.begin():
            recipient = self._session.scalar(
                select(WhatsAppBroadcastRecipient)
                .where(WhatsAppBroadcastRecipient.id == recipient_id)
                .with_for_update()
            )
            if (
                recipient is None
                or recipient.status is not WhatsAppBroadcastRecipientStatus.IN_PROGRESS
            ):
                return None
            broadcast = self._session.get(WhatsAppBroadcast, recipient.broadcast_id)
            if broadcast is None:
                raise EntityNotFoundError(
                    "WhatsAppBroadcast",
                    recipient.broadcast_id,
                )
            if self._template_for_broadcast(broadcast, templates) is None:
                self._block(recipient, "TEMPLATE_UNAVAILABLE", now=now)
                return None
            if not self._recipient_is_eligible(recipient, now=now):
                self._block(recipient, "CONSENT_OR_PHONE_CHANGED", now=now)
                return None
            existing = self._latest_message(recipient.id)
            if (
                existing is None
                or existing.dispatch_state is not WhatsAppDispatchState.PENDING
                or recipient.conversation_id is None
            ):
                self._block(recipient, "ATTEMPT_ALREADY_EXISTS", now=now)
                return None
            client_generated_id = existing.client_generated_id
            retry_of_message_id = existing.retry_of_message_id
            if client_generated_id is None:
                raise RuntimeError("Pending Broadcast Message has no UUID")
            message_type = broadcast.template_header_type or WhatsAppMessageType.TEXT
            attachment = self._attachment_input(broadcast)
            parameters = tuple(
                TemplateParameter(name=item.name, value=item.value)
                for item in broadcast.parameters
            )
            sent_by = self._broadcast_sender(broadcast)
            recipient.updated_at = now
            return _DispatchPlan(
                recipient.id,
                recipient.conversation_id,
                client_generated_id,
                retry_of_message_id,
                sent_by,
                message_type,
                attachment,
                broadcast.template_name,
                broadcast.template_language,
                parameters,
            )

    def _validation_snapshot(
        self,
        broadcast: WhatsAppBroadcast,
        *,
        recipients: tuple[WhatsAppBroadcastRecipient, ...],
        parameters: tuple[WhatsAppBroadcastTemplateParameter, ...],
        templates: tuple[ProviderTemplateSnapshot, ...],
        now: datetime,
    ) -> _ValidationSnapshot:
        issues: list[str] = []
        if not recipients:
            issues.append("NO_RECIPIENTS")
        template = self._template_for_broadcast(broadcast, templates)
        if template is None:
            issues.append("TEMPLATE_UNAVAILABLE_OR_CHANGED")
        try:
            if broadcast.header_media_ref is not None:
                media = self._storage.get_metadata(broadcast.header_media_ref)
                if media.storage_key != broadcast.header_media_storage_key:
                    issues.append("HEADER_MEDIA_CHANGED")
            elif broadcast.template_header_media_required:
                issues.append("HEADER_MEDIA_REQUIRED")
        except MediaStorageError:
            issues.append("HEADER_MEDIA_UNAVAILABLE")
        customer_ids = tuple(
            sorted({recipient.customer_id for recipient in recipients})
        )
        customers = tuple(
            self._session.scalars(
                select(Customer)
                .where(Customer.id.in_(customer_ids))
                .options(raiseload("*"))
            )
        )
        customers_by_id = {customer.id: customer for customer in customers}
        consent_by_key = WhatsAppConsentService(self._session).current_many(
            tuple(
                ConsentLookupKey(recipient.customer_id, recipient.normalized_phone)
                for recipient in recipients
            ),
            now=now,
        )
        consent_by_recipient: list[tuple[int, int]] = []
        for recipient in recipients:
            customer = customers_by_id.get(recipient.customer_id)
            if (
                customer is None
                or customer.deleted_at is not None
                or comparable_phone(customer.phone) != recipient.normalized_phone
            ):
                issues.append(f"RECIPIENT_{recipient.id}_PHONE_INVALID")
                continue
            current = consent_by_key.get(
                ConsentLookupKey(customer.id, recipient.normalized_phone)
            )
            if (
                current is None
                or current.decision is not WhatsAppConsentDecision.OPT_IN
            ):
                issues.append(f"RECIPIENT_{recipient.id}_NO_OPT_IN")
                continue
            consent_by_recipient.append((recipient.id, current.id))
        digest = self._validation_digest(
            broadcast,
            parameters,
            recipients,
            tuple(consent_by_recipient),
        )
        return _ValidationSnapshot(tuple(issues), tuple(consent_by_recipient), digest)

    def _recipient_is_eligible(
        self,
        recipient: WhatsAppBroadcastRecipient,
        *,
        now: datetime,
    ) -> bool:
        customer = self._session.get(Customer, recipient.customer_id)
        if (
            customer is None
            or customer.deleted_at is not None
            or comparable_phone(customer.phone) != recipient.normalized_phone
        ):
            return False
        current = WhatsAppConsentService(self._session).current(
            customer.id,
            recipient.normalized_phone,
            now=now,
        )
        return (
            current is not None and current.decision is WhatsAppConsentDecision.OPT_IN
        )

    def _conversation_for_recipient(
        self,
        recipient: WhatsAppBroadcastRecipient,
    ) -> WhatsAppConversation:
        conversation = self._session.scalar(
            select(WhatsAppConversation)
            .where(WhatsAppConversation.phone_match_key == recipient.normalized_phone)
            .with_for_update()
        )
        if conversation is None:
            conversation = WhatsAppConversation(
                customer_id=recipient.customer_id,
                external_phone=recipient.normalized_phone,
                phone_match_key=recipient.normalized_phone,
                display_name=recipient.customer_display_name,
                resolution_status=WhatsAppConversationResolution.RESOLVED,
            )
            self._session.add(conversation)
            self._session.flush()
        elif (
            conversation.customer_id != recipient.customer_id
            or conversation.resolution_status
            is not WhatsAppConversationResolution.RESOLVED
        ):
            raise WhatsAppBroadcastConflictError(
                "Recipient phone belongs to an unresolved or different conversation"
            )
        return conversation

    def _pending_broadcast_message(
        self,
        broadcast: WhatsAppBroadcast,
        recipient: WhatsAppBroadcastRecipient,
        previous: WhatsAppMessage | None,
        *,
        actor_user_id: int,
        client_generated_id: UUID,
    ) -> WhatsAppMessage:
        conversation_id = recipient.conversation_id
        if conversation_id is None:
            conversation = self._session.scalar(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.phone_match_key == recipient.normalized_phone
                )
            )
            conversation_id = conversation.id if conversation is not None else None
        if conversation_id is None:
            raise RuntimeError("Failed Broadcast recipient has no conversation")
        message_type = broadcast.template_header_type or WhatsAppMessageType.TEXT
        message = WhatsAppMessage(
            conversation_id=conversation_id,
            external_message_id=None,
            client_generated_id=client_generated_id,
            direction=WhatsAppDirection.OUTBOUND,
            message_type=message_type,
            origin=WhatsAppMessageOrigin.BROADCAST,
            body=None,
            sent_by_user_id=actor_user_id,
            retry_of_message_id=previous.id if previous is not None else None,
            broadcast_recipient_id=recipient.id,
            template_name=broadcast.template_name,
            template_language=broadcast.template_language,
            dispatch_state=WhatsAppDispatchState.PENDING,
            provider_state=None,
        )
        self._session.add(message)
        self._session.flush()
        attachment = self._attachment_input(broadcast)
        if attachment is not None:
            self._session.add(
                WhatsAppAttachment(
                    message_id=message.id,
                    provider_media_id=None,
                    media_type=message_type,
                    mime_type=attachment.mime_type,
                    filename=attachment.filename,
                    size_bytes=attachment.size_bytes,
                    storage_key=attachment.storage_key,
                    storage_status=WhatsAppStorageStatus.AVAILABLE,
                )
            )
        return message

    def _recover_stale_claims(
        self,
        broadcast: WhatsAppBroadcast,
        *,
        now: datetime,
    ) -> None:
        threshold = now - self._claim_timeout
        stale = tuple(
            self._session.scalars(
                select(WhatsAppBroadcastRecipient)
                .where(
                    WhatsAppBroadcastRecipient.broadcast_id == broadcast.id,
                    WhatsAppBroadcastRecipient.status
                    == WhatsAppBroadcastRecipientStatus.IN_PROGRESS,
                    WhatsAppBroadcastRecipient.claimed_at < threshold,
                )
                .order_by(WhatsAppBroadcastRecipient.id)
                .with_for_update(skip_locked=True)
            )
        )
        latest_by_recipient = self._latest_messages_for_recipients_locked(
            tuple(recipient.id for recipient in stale)
        )
        for recipient in stale:
            message = latest_by_recipient.get(recipient.id)
            if (
                message is None
                or message.dispatch_state is WhatsAppDispatchState.PENDING
            ):
                recipient.status = WhatsAppBroadcastRecipientStatus.READY
                recipient.claim_token = None
                recipient.claimed_at = None
                reason = "SAFE_RECLAIM"
            elif message.dispatch_state is WhatsAppDispatchState.IN_PROGRESS:
                message.dispatch_state = WhatsAppDispatchState.UNKNOWN
                message.provider_error_code = "STALE_IN_PROGRESS"
                message.provider_error_message = "Provider acceptance is unknown"
                message.updated_at = later_datetime(message.updated_at, now)
                recipient.claim_token = None
                recipient.claimed_at = None
                reason = "MARKED_UNKNOWN"
            else:
                reason = "ALREADY_RECONCILED"
            if message is not None:
                recompute_broadcast_recipient_projection(
                    self._session,
                    recipient,
                    now=now,
                )
            else:
                recipient.updated_at = now
            self._audit(
                broadcast.id,
                WhatsAppBroadcastAuditEventType.STALE_CLAIM_RECOVERED,
                occurred_at=now,
                recipient_id=recipient.id,
                message_id=message.id if message is not None else None,
                reason_code=reason,
            )

    def _complete_if_idle(self, broadcast: WhatsAppBroadcast, *, now: datetime) -> None:
        remaining = self._remaining_count(broadcast.id)
        if remaining != 0:
            return
        broadcast.status = WhatsAppBroadcastStatus.COMPLETED
        if broadcast.first_completed_at is None:
            broadcast.first_completed_at = now
        broadcast.last_completed_at = now
        broadcast.updated_at = now
        self._audit(
            broadcast.id,
            WhatsAppBroadcastAuditEventType.COMPLETED,
            occurred_at=now,
        )

    def _block(
        self,
        recipient: WhatsAppBroadcastRecipient,
        reason: str,
        *,
        now: datetime,
    ) -> None:
        recipient.status = WhatsAppBroadcastRecipientStatus.BLOCKED
        recipient.reason_code = reason
        recipient.claim_token = None
        recipient.claimed_at = None
        recipient.updated_at = now
        self._audit(
            recipient.broadcast_id,
            WhatsAppBroadcastAuditEventType.BLOCKED,
            occurred_at=now,
            recipient_id=recipient.id,
            reason_code=reason,
        )

    def _process_result(
        self,
        broadcast: WhatsAppBroadcast,
        claimed_count: int,
        replayed: bool,
        *,
        completed_count: int = 0,
    ) -> BroadcastProcessResult:
        return BroadcastProcessResult(
            broadcast.id,
            claimed_count,
            completed_count,
            self._remaining_count(broadcast.id),
            replayed,
        )

    def _remaining_count(self, broadcast_id: int) -> int:
        value = self._session.scalar(
            select(func.count(WhatsAppBroadcastRecipient.id)).where(
                WhatsAppBroadcastRecipient.broadcast_id == broadcast_id,
                WhatsAppBroadcastRecipient.status.in_(
                    {
                        WhatsAppBroadcastRecipientStatus.READY,
                        WhatsAppBroadcastRecipientStatus.IN_PROGRESS,
                    }
                ),
            )
        )
        return value or 0

    def _template_for_broadcast(
        self,
        broadcast: WhatsAppBroadcast,
        templates: tuple[ProviderTemplateSnapshot, ...],
    ) -> ProviderTemplateSnapshot | None:
        template = next(
            (
                item
                for item in templates
                if item.external_id == broadcast.template_external_id
                and item.name == broadcast.template_name
                and item.language == broadcast.template_language
            ),
            None,
        )
        if (
            template is None
            or not self._template_is_sendable(template)
            or self._template_signature(template)
            != broadcast.template_component_signature
        ):
            return None
        return template

    def _find_template(self, external_id: str) -> ProviderTemplateSnapshot:
        normalized = self._required_text(external_id, "Template external ID")
        template = next(
            (
                item
                for item in self._provider.list_templates()
                if item.external_id == normalized and self._template_is_sendable(item)
            ),
            None,
        )
        if template is None:
            raise InvalidWhatsAppBroadcastError(
                "Approved sendable marketing template was not found"
            )
        return template

    @staticmethod
    def _template_is_sendable(template: ProviderTemplateSnapshot) -> bool:
        return (
            template.category.upper() == "MARKETING"
            and template.status.upper() == "APPROVED"
            and template.supported_for_send
        )

    def _header_media(
        self,
        template: ProviderTemplateSnapshot,
        media_ref: UUID | None,
    ) -> StoredMedia | None:
        if media_ref is None:
            if template.header_media_required:
                raise InvalidWhatsAppBroadcastError(
                    "Selected template requires header media"
                )
            return None
        expected = self._message_type(template.header_type)
        if expected not in {WhatsAppMessageType.IMAGE, WhatsAppMessageType.DOCUMENT}:
            raise InvalidWhatsAppBroadcastError(
                "Selected template does not accept header media"
            )
        try:
            media = self._storage.get_metadata(media_ref)
        except MediaStorageError as error:
            raise InvalidWhatsAppBroadcastError(
                "Broadcast header media is unavailable"
            ) from error
        if media.media_type is not expected:
            raise InvalidWhatsAppBroadcastError(
                "Broadcast header media type does not match the template"
            )
        return media

    @staticmethod
    def _message_type(header_type: TemplateHeaderType) -> WhatsAppMessageType:
        if header_type is TemplateHeaderType.IMAGE:
            return WhatsAppMessageType.IMAGE
        if header_type is TemplateHeaderType.DOCUMENT:
            return WhatsAppMessageType.DOCUMENT
        return WhatsAppMessageType.TEXT

    @staticmethod
    def _normalize_parameters(
        parameters: tuple[BroadcastParameterInput, ...],
    ) -> tuple[BroadcastParameterInput, ...]:
        normalized = tuple(
            BroadcastParameterInput(
                WhatsAppBroadcastService._required_text(item.name, "Parameter name"),
                WhatsAppBroadcastService._required_text(item.value, "Parameter value"),
            )
            for item in parameters
        )
        names = tuple(item.name for item in normalized)
        if len(names) != len(set(names)):
            raise InvalidWhatsAppBroadcastError(
                "Broadcast parameter names must be unique"
            )
        return normalized

    @staticmethod
    def _validate_parameters(
        template: ProviderTemplateSnapshot,
        parameters: tuple[BroadcastParameterInput, ...],
    ) -> None:
        if {item.name for item in parameters} != set(template.parameter_names):
            raise InvalidWhatsAppBroadcastError(
                "Broadcast parameters do not match the selected template"
            )

    @staticmethod
    def _template_signature(template: ProviderTemplateSnapshot) -> str:
        payload = "\x1f".join(
            (
                template.external_id,
                template.name,
                template.language,
                template.category.upper(),
                template.status.upper(),
                template.header_type.value,
                "1" if template.header_media_required else "0",
                "1" if template.supported_for_send else "0",
                *template.parameter_names,
            )
        )
        return sha256(payload.encode()).hexdigest()

    @staticmethod
    def _validation_digest(
        broadcast: WhatsAppBroadcast,
        parameters: tuple[WhatsAppBroadcastTemplateParameter, ...],
        recipients: tuple[WhatsAppBroadcastRecipient, ...],
        consent_ids: tuple[tuple[int, int], ...],
    ) -> str:
        values = [
            str(broadcast.id),
            str(broadcast.version),
            broadcast.label,
            broadcast.external_campaign_reference or "",
            broadcast.template_component_signature,
            str(broadcast.header_media_ref or ""),
        ]
        values.extend(f"{item.name}={item.value}" for item in parameters)
        values.extend(
            f"{recipient.id}:{recipient.customer_id}:{recipient.normalized_phone}"
            for recipient in recipients
        )
        values.extend(
            f"{recipient_id}:{event_id}" for recipient_id, event_id in consent_ids
        )
        return sha256("\x1f".join(values).encode()).hexdigest()

    def _validation_recipients(
        self,
        broadcast_id: int,
        *,
        for_update: bool,
    ) -> tuple[WhatsAppBroadcastRecipient, ...]:
        statement = (
            select(WhatsAppBroadcastRecipient)
            .where(WhatsAppBroadcastRecipient.broadcast_id == broadcast_id)
            .order_by(WhatsAppBroadcastRecipient.id)
            .options(raiseload("*"))
        )
        if for_update:
            statement = statement.with_for_update()
        return tuple(self._session.scalars(statement))

    def _validation_parameters(
        self,
        broadcast_id: int,
    ) -> tuple[WhatsAppBroadcastTemplateParameter, ...]:
        return tuple(
            self._session.scalars(
                select(WhatsAppBroadcastTemplateParameter)
                .where(WhatsAppBroadcastTemplateParameter.broadcast_id == broadcast_id)
                .order_by(WhatsAppBroadcastTemplateParameter.position)
                .options(raiseload("*"))
            )
        )

    def _assert_create_replay(
        self,
        existing: WhatsAppBroadcast,
        create_input: BroadcastCreateInput,
        *,
        label: str,
        external_reference: str | None,
        template: ProviderTemplateSnapshot,
        parameters: tuple[BroadcastParameterInput, ...],
        media: StoredMedia | None,
    ) -> None:
        existing_parameters = tuple(
            BroadcastParameterInput(item.name, item.value)
            for item in existing.parameters
        )
        if not (
            existing.label == label
            and existing.external_campaign_reference == external_reference
            and existing.template_external_id == template.external_id
            and existing_parameters == parameters
            and existing.header_media_ref
            == (media.media_ref if media is not None else None)
            and existing.created_by_user_id == create_input.created_by_user_id
        ):
            raise WhatsAppBroadcastConflictError(
                "Broadcast client_generated_id was reused with different data"
            )

    @staticmethod
    def _attachment_input(
        broadcast: WhatsAppBroadcast,
    ) -> OutboundAttachmentInput | None:
        if broadcast.header_media_storage_key is None:
            return None
        if broadcast.header_media_mime_type is None:
            raise RuntimeError("Persisted Broadcast header media has no MIME type")
        return OutboundAttachmentInput(
            provider_media_id=None,
            storage_key=broadcast.header_media_storage_key,
            mime_type=broadcast.header_media_mime_type,
            filename=broadcast.header_media_filename,
            size_bytes=broadcast.header_media_size_bytes,
        )

    def _latest_message(self, recipient_id: int) -> WhatsAppMessage | None:
        return self._session.scalar(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.broadcast_recipient_id == recipient_id)
            .order_by(WhatsAppMessage.id.desc())
            .limit(1)
        )

    def _latest_messages_for_recipients_locked(
        self,
        recipient_ids: tuple[int, ...],
    ) -> dict[int, WhatsAppMessage]:
        if not recipient_ids:
            return {}
        messages = tuple(
            self._session.scalars(
                select(WhatsAppMessage)
                .where(WhatsAppMessage.broadcast_recipient_id.in_(recipient_ids))
                .order_by(WhatsAppMessage.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        latest: dict[int, WhatsAppMessage] = {}
        for message in messages:
            recipient_id = message.broadcast_recipient_id
            if recipient_id is None:
                raise RuntimeError("Broadcast Message has no recipient")
            latest[recipient_id] = message
        return latest

    @staticmethod
    def _broadcast_sender(broadcast: WhatsAppBroadcast) -> int:
        sent_by = broadcast.started_by_user_id or broadcast.confirmed_by_user_id
        if sent_by is None:
            raise RuntimeError("Started Broadcast has no initiating user")
        return sent_by

    @staticmethod
    def _message_failed(message: WhatsAppMessage) -> bool:
        return (
            message.dispatch_state is WhatsAppDispatchState.DEFINITIVE_FAILED
            or message.provider_state is WhatsAppProviderState.FAILED
        )

    def _broadcast_for_update(self, broadcast_id: int) -> WhatsAppBroadcast:
        broadcast = self._session.scalar(
            select(WhatsAppBroadcast)
            .where(WhatsAppBroadcast.id == broadcast_id)
            .with_for_update()
        )
        if broadcast is None:
            raise EntityNotFoundError("WhatsAppBroadcast", broadcast_id)
        return broadcast

    @staticmethod
    def _require_draft_version(
        broadcast: WhatsAppBroadcast,
        expected_version: int,
    ) -> None:
        if (
            broadcast.status is not WhatsAppBroadcastStatus.DRAFT
            or broadcast.version != expected_version
        ):
            raise WhatsAppBroadcastConflictError(
                "Broadcast is immutable or its expected version is stale"
            )

    def _command_exists(self, broadcast_id: int, command_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(WhatsAppBroadcastAuditEvent.id).where(
                    WhatsAppBroadcastAuditEvent.broadcast_id == broadcast_id,
                    WhatsAppBroadcastAuditEvent.command_id == command_id,
                )
            )
            is not None
        )

    def _audit(
        self,
        broadcast_id: int,
        event_type: WhatsAppBroadcastAuditEventType,
        *,
        occurred_at: datetime,
        actor_user_id: int | None = None,
        command_id: UUID | None = None,
        recipient_id: int | None = None,
        message_id: int | None = None,
        reason_code: str | None = None,
        affected_count: int | None = None,
    ) -> None:
        self._session.add(
            WhatsAppBroadcastAuditEvent(
                broadcast_id=broadcast_id,
                recipient_id=recipient_id,
                message_id=message_id,
                command_id=command_id,
                event_type=event_type,
                reason_code=reason_code,
                actor_user_id=actor_user_id,
                affected_count=affected_count,
                occurred_at=occurred_at,
            )
        )

    @staticmethod
    def _required_text(value: str, label: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise InvalidWhatsAppBroadcastError(f"{label} is required")
        return normalized

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
