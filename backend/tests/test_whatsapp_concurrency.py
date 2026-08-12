from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event, Lock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

import app.services.whatsapp_consent_service as consent_module
import app.services.whatsapp_message_service as message_module
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Customer,
    User,
    UserRole,
    WhatsAppAttachment,
    WhatsAppBroadcast,
    WhatsAppBroadcastAuditEvent,
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppBroadcastStatus,
    WhatsAppBroadcastTemplateParameter,
    WhatsAppConsentDecision,
    WhatsAppConsentSource,
    WhatsAppConversation,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMarketingConsentEvent,
    WhatsAppMessage,
    WhatsAppMessageOrigin,
    WhatsAppMessageStatusEvent,
    WhatsAppMessageType,
    WhatsAppProviderState,
)
from app.services.customer_identity_service import (
    acquire_advisory_locks as acquire_real_advisory_locks,
)
from app.services.errors import (
    WhatsAppBroadcastConflictError,
    WhatsAppIdempotencyConflictError,
)
from app.services.whatsapp_broadcast_service import (
    BroadcastCreateInput,
    WhatsAppBroadcastService,
)
from app.services.whatsapp_consent_service import (
    ConsentEventInput,
    WhatsAppConsentService,
)
from app.services.whatsapp_message_service import (
    OutboundMessageInput,
    OutboundMessageResult,
    WhatsAppMessageService,
)
from app.services.whatsapp_status_service import (
    ProviderStatusInput,
    WhatsAppStatusService,
)
from app.whatsapp import (
    FakeMediaStorage,
    FakeWhatsAppProvider,
    ProviderSendResult,
    ProviderTemplateSnapshot,
    SendTemplateRequest,
    TemplateHeaderType,
)

NOW = datetime.now(UTC).replace(microsecond=0)
TEMPLATE = ProviderTemplateSnapshot(
    external_id="crm-013-marketing",
    name="crm_013_offer",
    language="es_AR",
    category="MARKETING",
    status="APPROVED",
    header_type=TemplateHeaderType.NONE,
)
TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class PersistedContext:
    user_id: int
    customer_ids: tuple[int, ...]
    broadcast_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadyBroadcast:
    context: PersistedContext
    broadcast_id: int
    recipient_ids: tuple[int, ...]


class CoordinatedTemplateProvider(FakeWhatsAppProvider):
    def __init__(
        self,
        *,
        send_barrier: Barrier | None = None,
        entered: Event | None = None,
        release: Event | None = None,
        transaction_is_open: Callable[[], bool] | None = None,
        external_message_id: str | None = None,
    ) -> None:
        super().__init__(
            now=NOW,
            freeform_window=timedelta(hours=24),
            templates=(TEMPLATE,),
        )
        self._send_barrier = send_barrier
        self._entered = entered
        self._release = release
        self._transaction_is_open = transaction_is_open
        self._external_message_id = external_message_id
        self._request_lock = Lock()

    def send_template(self, request: SendTemplateRequest) -> ProviderSendResult:
        if self._transaction_is_open is not None:
            assert not self._transaction_is_open()
        if self._entered is not None:
            self._entered.set()
        if self._send_barrier is not None:
            self._send_barrier.wait(timeout=TIMEOUT_SECONDS)
        if self._release is not None:
            assert self._release.wait(timeout=TIMEOUT_SECONDS)
        with self._request_lock:
            if self._external_message_id is None:
                return super().send_template(request)
            self.requests.append(request)
            return ProviderSendResult(
                external_message_id=self._external_message_id,
                accepted_at=NOW,
                initial_state=WhatsAppProviderState.SENT,
            )


def test_concurrent_consent_idempotency_replays_or_conflicts_without_db_errors() -> (
    None
):
    context = _persist_identities(1)
    same_id = uuid4()
    conflict_id = uuid4()
    try:
        same_input = _consent_input(
            same_id,
            context.customer_ids[0],
            context.user_id,
            WhatsAppConsentDecision.OPT_IN,
        )
        barrier = Barrier(2)

        def append_same() -> tuple[int, bool]:
            barrier.wait(timeout=TIMEOUT_SECONDS)
            with SessionLocal() as session:
                result = WhatsAppConsentService(session).append(same_input, now=NOW)
                return result.event.id, result.created

        with ThreadPoolExecutor(max_workers=2) as same_executor:
            results = tuple(same_executor.submit(append_same) for _ in range(2))
            resolved = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in results
            )
        assert resolved[0][0] == resolved[1][0]
        assert sorted(item[1] for item in resolved) == [False, True]

        conflict_barrier = Barrier(2)

        def append_conflicting(decision: WhatsAppConsentDecision) -> str:
            event_input = _consent_input(
                conflict_id,
                context.customer_ids[0],
                context.user_id,
                decision,
            )
            conflict_barrier.wait(timeout=TIMEOUT_SECONDS)
            try:
                with SessionLocal() as session:
                    WhatsAppConsentService(session).append(event_input, now=NOW)
            except WhatsAppBroadcastConflictError:
                return "conflict"
            return "created"

        with ThreadPoolExecutor(max_workers=2) as conflict_executor:
            futures = (
                conflict_executor.submit(
                    append_conflicting,
                    WhatsAppConsentDecision.OPT_IN,
                ),
                conflict_executor.submit(
                    append_conflicting,
                    WhatsAppConsentDecision.OPT_OUT,
                ),
            )
            outcomes = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in futures
            )
        assert sorted(outcomes) == ["conflict", "created"]
        with SessionLocal() as verification:
            assert (
                verification.scalar(
                    select(func.count(WhatsAppMarketingConsentEvent.id)).where(
                        WhatsAppMarketingConsentEvent.client_event_id.in_(
                            {same_id, conflict_id}
                        )
                    )
                )
                == 2
            )
    finally:
        _cleanup(context)


def test_concurrent_broadcast_create_and_lifecycle_commands_are_idempotent() -> None:
    context = _persist_identities(1)
    provider = FakeWhatsAppProvider(now=NOW, templates=(TEMPLATE,))
    storage = FakeMediaStorage()
    create_id = uuid4()
    created_broadcast_id: int | None = None
    conflicting_broadcast_id: int | None = None
    ready: ReadyBroadcast | None = None
    try:
        create_input = _broadcast_create_input(create_id, context.user_id, "Same")
        barrier = Barrier(2)

        def create_same() -> tuple[int, bool]:
            barrier.wait(timeout=TIMEOUT_SECONDS)
            with SessionLocal() as session:
                broadcast, created = _broadcast_service(
                    session,
                    provider,
                    storage,
                ).create(create_input, now=NOW)
                return broadcast.id, created

        with ThreadPoolExecutor(max_workers=2) as create_executor:
            create_futures = tuple(
                create_executor.submit(create_same) for _ in range(2)
            )
            results = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in create_futures
            )
        assert results[0][0] == results[1][0]
        assert sorted(result[1] for result in results) == [False, True]
        created_broadcast_id = results[0][0]

        conflicting_create_id = uuid4()
        conflict_barrier = Barrier(2)

        def create_conflicting(label: str) -> tuple[str, int | None]:
            conflict_barrier.wait(timeout=TIMEOUT_SECONDS)
            try:
                with SessionLocal() as session:
                    broadcast, _created = _broadcast_service(
                        session,
                        provider,
                        storage,
                    ).create(
                        _broadcast_create_input(
                            conflicting_create_id,
                            context.user_id,
                            label,
                        ),
                        now=NOW,
                    )
                    return "created", broadcast.id
            except WhatsAppBroadcastConflictError:
                return "conflict", None

        with ThreadPoolExecutor(max_workers=2) as conflict_executor:
            conflict_futures = (
                conflict_executor.submit(create_conflicting, "Payload A"),
                conflict_executor.submit(create_conflicting, "Payload B"),
            )
            conflict_results = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in conflict_futures
            )
        assert sorted(result[0] for result in conflict_results) == [
            "conflict",
            "created",
        ]
        conflicting_broadcast_id = next(
            result[1] for result in conflict_results if result[1] is not None
        )

        ready = _ready_broadcast(
            1,
            start=False,
            existing_context=context,
        )
        command_id = uuid4()
        start_barrier = Barrier(2)

        def start_same() -> int:
            start_barrier.wait(timeout=TIMEOUT_SECONDS)
            with SessionLocal() as session:
                return (
                    _broadcast_service(session, provider, storage)
                    .start(
                        ready.broadcast_id,
                        command_id=command_id,
                        actor_user_id=context.user_id,
                        now=NOW,
                    )
                    .id
                )

        with ThreadPoolExecutor(max_workers=2) as start_executor:
            start_futures = tuple(start_executor.submit(start_same) for _ in range(2))
            assert {
                future.result(timeout=TIMEOUT_SECONDS) for future in start_futures
            } == {ready.broadcast_id}
        with SessionLocal() as verification:
            assert (
                verification.scalar(
                    select(func.count(WhatsAppBroadcastAuditEvent.id)).where(
                        WhatsAppBroadcastAuditEvent.broadcast_id == ready.broadcast_id,
                        WhatsAppBroadcastAuditEvent.command_id == command_id,
                    )
                )
                == 1
            )
    finally:
        broadcast_ids = tuple(
            item
            for item in (
                created_broadcast_id,
                conflicting_broadcast_id,
                ready.broadcast_id if ready is not None else None,
            )
            if item is not None
        )
        _cleanup(
            PersistedContext(
                context.user_id,
                context.customer_ids,
                broadcast_ids,
            )
        )


def test_concurrent_outbound_uuid_dispatches_once_and_changed_payload_conflicts() -> (
    None
):
    context = _persist_identities(1)
    conversation_id = _persist_conversation(context.customer_ids[0])
    provider = CoordinatedTemplateProvider()
    message_id = uuid4()
    try:
        message_input = _human_message_input(
            conversation_id,
            context.user_id,
            message_id,
            "Mismo texto",
        )
        barrier = Barrier(2)

        def send_same() -> OutboundMessageResult:
            barrier.wait(timeout=TIMEOUT_SECONDS)
            with SessionLocal() as session:
                return WhatsAppMessageService(session, provider).send(
                    message_input,
                    now=NOW,
                )

        with ThreadPoolExecutor(max_workers=2) as same_executor:
            same_futures = tuple(same_executor.submit(send_same) for _ in range(2))
            results = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in same_futures
            )
        assert results[0].message_id == results[1].message_id
        assert sorted(result.created for result in results) == [False, True]
        assert len(provider.requests) == 1

        changed_id = uuid4()
        changed_barrier = Barrier(2)

        def send_changed(body: str) -> str:
            changed_barrier.wait(timeout=TIMEOUT_SECONDS)
            try:
                with SessionLocal() as session:
                    WhatsAppMessageService(session, provider).send(
                        _human_message_input(
                            conversation_id,
                            context.user_id,
                            changed_id,
                            body,
                        ),
                        now=NOW,
                    )
            except WhatsAppIdempotencyConflictError:
                return "conflict"
            return "created"

        with ThreadPoolExecutor(max_workers=2) as changed_executor:
            changed_futures = (
                changed_executor.submit(send_changed, "Texto A"),
                changed_executor.submit(send_changed, "Texto B"),
            )
            outcomes = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in changed_futures
            )
        assert sorted(outcomes) == ["conflict", "created"]
        assert len(provider.requests) == 2
        with SessionLocal() as verification:
            assert (
                verification.scalar(
                    select(func.count(WhatsAppMessage.id)).where(
                        WhatsAppMessage.client_generated_id.in_(
                            {message_id, changed_id}
                        )
                    )
                )
                == 2
            )
    finally:
        _cleanup(context)


def test_two_processors_claim_distinct_recipients_without_double_send() -> None:
    ready = _ready_broadcast(2)
    provider = CoordinatedTemplateProvider(send_barrier=Barrier(2))
    storage = FakeMediaStorage()
    start_barrier = Barrier(2)
    try:

        def process_once() -> int:
            start_barrier.wait(timeout=TIMEOUT_SECONDS)
            with SessionLocal() as session:
                result = _broadcast_service(
                    session,
                    provider,
                    storage,
                    batch_size=1,
                ).process_batch(
                    ready.broadcast_id,
                    command_id=uuid4(),
                    actor_user_id=ready.context.user_id,
                    now=NOW,
                )
                return result.claimed_count

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = tuple(executor.submit(process_once) for _ in range(2))
            claimed = tuple(
                future.result(timeout=TIMEOUT_SECONDS) for future in futures
            )
        assert claimed == (1, 1)
        assert len(provider.requests) == 2
        assert len({request.recipient.phone for request in provider.requests}) == 2
        with SessionLocal() as verification:
            messages = tuple(
                verification.scalars(
                    select(WhatsAppMessage).where(
                        WhatsAppMessage.broadcast_recipient_id.in_(ready.recipient_ids)
                    )
                )
            )
            assert len(messages) == 2
            assert {message.broadcast_recipient_id for message in messages} == set(
                ready.recipient_ids
            )
            assert all(message.retry_of_message_id is None for message in messages)
    finally:
        _cleanup(ready.context)


@pytest.mark.parametrize("winner", ("opt_out", "dispatch"))
def test_opt_out_and_dispatch_start_share_one_serialization_lock(
    monkeypatch: pytest.MonkeyPatch,
    winner: str,
) -> None:
    ready = _ready_broadcast(1)
    storage = FakeMediaStorage()
    lock_winner = Event()
    waiter_started = Event()
    provider_entered = Event()
    provider_release = Event()
    process_session: Session | None = None
    provider: CoordinatedTemplateProvider | None = None
    original_consent_acquire = acquire_real_advisory_locks
    original_message_acquire = acquire_real_advisory_locks

    def has_shared_lock(identities: tuple[tuple[str, str], ...]) -> bool:
        return any(
            namespace == "whatsapp-consent-dispatch" for namespace, _ in identities
        )

    def consent_acquire(
        session: Session,
        identities: tuple[tuple[str, str], ...],
    ) -> None:
        if not has_shared_lock(identities):
            original_consent_acquire(session, identities)
            return
        if winner == "opt_out":
            original_consent_acquire(session, identities)
            lock_winner.set()
            assert waiter_started.wait(timeout=TIMEOUT_SECONDS)
        else:
            waiter_started.set()
            original_consent_acquire(session, identities)

    def message_acquire(
        session: Session,
        identities: tuple[tuple[str, str], ...],
    ) -> None:
        if not has_shared_lock(identities):
            original_message_acquire(session, identities)
            return
        if winner == "dispatch":
            original_message_acquire(session, identities)
            lock_winner.set()
            assert waiter_started.wait(timeout=TIMEOUT_SECONDS)
        else:
            waiter_started.set()
            original_message_acquire(session, identities)

    monkeypatch.setattr(consent_module, "acquire_advisory_locks", consent_acquire)
    monkeypatch.setattr(message_module, "acquire_advisory_locks", message_acquire)
    try:

        def opt_out() -> None:
            with SessionLocal() as session:
                WhatsAppConsentService(session).append(
                    _consent_input(
                        uuid4(),
                        ready.context.customer_ids[0],
                        ready.context.user_id,
                        WhatsAppConsentDecision.OPT_OUT,
                    ),
                    now=NOW,
                )

        def process() -> int:
            nonlocal process_session, provider
            with SessionLocal() as session:
                process_session = session
                provider = CoordinatedTemplateProvider(
                    entered=provider_entered,
                    release=provider_release if winner == "dispatch" else None,
                    transaction_is_open=session.in_transaction,
                )
                return (
                    _broadcast_service(session, provider, storage)
                    .process_batch(
                        ready.broadcast_id,
                        command_id=uuid4(),
                        actor_user_id=ready.context.user_id,
                        now=NOW,
                    )
                    .claimed_count
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(opt_out if winner == "opt_out" else process)
            assert lock_winner.wait(timeout=TIMEOUT_SECONDS)
            second = executor.submit(process if winner == "opt_out" else opt_out)
            if winner == "dispatch":
                assert provider_entered.wait(timeout=TIMEOUT_SECONDS)
                second.result(timeout=TIMEOUT_SECONDS)
                provider_release.set()
            first.result(timeout=TIMEOUT_SECONDS)
            second.result(timeout=TIMEOUT_SECONDS)

        assert process_session is not None
        assert provider is not None
        assert not process_session.in_transaction()
        assert len(provider.requests) == (0 if winner == "opt_out" else 1)
        with SessionLocal() as verification:
            recipient = verification.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            assert recipient is not None
            current = WhatsAppConsentService(verification).current(
                ready.context.customer_ids[0],
                recipient.normalized_phone,
                now=NOW + timedelta(seconds=2),
            )
            assert current is not None
            assert current.decision is WhatsAppConsentDecision.OPT_OUT
            if winner == "opt_out":
                assert recipient.status is WhatsAppBroadcastRecipientStatus.BLOCKED
            else:
                assert recipient.status is WhatsAppBroadcastRecipientStatus.SENT
    finally:
        provider_release.set()
        _cleanup(ready.context)


def test_old_attempt_webhook_cannot_overwrite_new_retry_projection() -> None:
    ready = _ready_broadcast(1)
    provider = FakeWhatsAppProvider(now=NOW, templates=(TEMPLATE,))
    storage = FakeMediaStorage()
    provider_entered = Event()
    provider_release = Event()
    retry_provider = CoordinatedTemplateProvider(
        entered=provider_entered,
        release=provider_release,
        external_message_id=f"crm-013-retry-{uuid4()}",
    )
    try:
        with SessionLocal() as session:
            _broadcast_service(session, provider, storage).process_batch(
                ready.broadcast_id,
                command_id=uuid4(),
                actor_user_id=ready.context.user_id,
                now=NOW,
            )
        with SessionLocal() as session:
            old = session.scalar(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.broadcast_recipient_id == ready.recipient_ids[0]
                )
            )
            assert old is not None
            assert old.external_message_id is not None
            old_id = old.id
            old_external_id = old.external_message_id
        with SessionLocal() as session:
            WhatsAppStatusService(session).record(
                ProviderStatusInput(
                    external_message_id=old_external_id,
                    state=WhatsAppProviderState.FAILED,
                    occurred_at=NOW + timedelta(seconds=1),
                    error_code="FAILED",
                    error_message="Failed",
                ),
                received_at=NOW + timedelta(seconds=1),
            )
        with SessionLocal() as session:
            retry = _broadcast_service(session, provider, storage).retry_failed(
                ready.broadcast_id,
                command_id=uuid4(),
                recipient_ids=ready.recipient_ids,
                actor_user_id=ready.context.user_id,
                now=NOW + timedelta(seconds=2),
            )
            assert len(retry.created_message_ids) == 1
            retry_id = retry.created_message_ids[0]

        def record_old_read() -> None:
            with SessionLocal() as session:
                WhatsAppStatusService(session).record(
                    ProviderStatusInput(
                        external_message_id=old_external_id,
                        state=WhatsAppProviderState.READ,
                        occurred_at=NOW + timedelta(hours=1),
                    ),
                    received_at=NOW + timedelta(seconds=3),
                )

        def process_retry() -> None:
            with SessionLocal() as session:
                result = _broadcast_service(
                    session,
                    retry_provider,
                    storage,
                ).process_batch(
                    ready.broadcast_id,
                    command_id=uuid4(),
                    actor_user_id=ready.context.user_id,
                    now=NOW + timedelta(seconds=3),
                )
                assert result.claimed_count == 1
                assert result.completed_count == 1

        with ThreadPoolExecutor(max_workers=2) as executor:
            process_future = executor.submit(process_retry)
            assert provider_entered.wait(timeout=TIMEOUT_SECONDS)
            status_future = executor.submit(record_old_read)
            status_future.result(timeout=TIMEOUT_SECONDS)
            provider_release.set()
            process_future.result(timeout=TIMEOUT_SECONDS)
        with SessionLocal() as verification:
            recipient = verification.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            old = verification.get(WhatsAppMessage, old_id)
            latest = verification.get(WhatsAppMessage, retry_id)
            assert recipient is not None
            assert old is not None
            assert latest is not None
            assert old.provider_state is WhatsAppProviderState.READ
            assert latest.id > old.id
            assert latest.provider_state is WhatsAppProviderState.SENT
            assert recipient.status is WhatsAppBroadcastRecipientStatus.SENT
            assert recipient.safe_error_code is None
            assert len(provider.requests) == 1
            assert len(retry_provider.requests) == 1
    finally:
        provider_release.set()
        _cleanup(ready.context)


def test_webhook_before_provider_reconciliation_is_attached_monotonically() -> None:
    ready = _ready_broadcast(1)
    external_id = f"crm-013-{uuid4()}"
    provider_entered = Event()
    provider_release = Event()
    provider = CoordinatedTemplateProvider(
        entered=provider_entered,
        release=provider_release,
        external_message_id=external_id,
    )
    storage = FakeMediaStorage()
    try:

        def process() -> None:
            with SessionLocal() as session:
                _broadcast_service(session, provider, storage).process_batch(
                    ready.broadcast_id,
                    command_id=uuid4(),
                    actor_user_id=ready.context.user_id,
                    now=NOW,
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            process_future = executor.submit(process)
            assert provider_entered.wait(timeout=TIMEOUT_SECONDS)

            def webhook() -> None:
                with SessionLocal() as session:
                    result = WhatsAppStatusService(session).record(
                        ProviderStatusInput(
                            external_message_id=external_id,
                            state=WhatsAppProviderState.DELIVERED,
                            occurred_at=NOW + timedelta(seconds=1),
                        ),
                        received_at=NOW + timedelta(seconds=1),
                    )
                    assert result.message_id is None

            webhook_future = executor.submit(webhook)
            webhook_future.result(timeout=TIMEOUT_SECONDS)
            provider_release.set()
            process_future.result(timeout=TIMEOUT_SECONDS)
        with SessionLocal() as verification:
            message = verification.scalar(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.broadcast_recipient_id == ready.recipient_ids[0]
                )
            )
            recipient = verification.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            event = verification.scalar(
                select(WhatsAppMessageStatusEvent).where(
                    WhatsAppMessageStatusEvent.external_message_id == external_id
                )
            )
            assert message is not None
            assert recipient is not None
            assert event is not None
            assert event.message_id == message.id
            assert message.provider_state is WhatsAppProviderState.DELIVERED
            assert recipient.status is WhatsAppBroadcastRecipientStatus.DELIVERED
            assert len(provider.requests) == 1
    finally:
        provider_release.set()
        _cleanup(ready.context)


def test_concurrent_stale_claim_recovery_reuses_pending_and_never_resends_unknown() -> (
    None
):
    ready = _ready_broadcast(1)
    provider = FakeWhatsAppProvider(now=NOW, templates=(TEMPLATE,))
    storage = FakeMediaStorage()
    message_id, client_id = _seed_claimed_message(ready, dispatch_started=False)
    barrier = Barrier(2)
    try:

        def recover() -> None:
            barrier.wait(timeout=TIMEOUT_SECONDS)
            with SessionLocal() as session:
                _broadcast_service(session, provider, storage).process_batch(
                    ready.broadcast_id,
                    command_id=uuid4(),
                    actor_user_id=ready.context.user_id,
                    now=NOW,
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = tuple(executor.submit(recover) for _ in range(2))
            for future in futures:
                future.result(timeout=TIMEOUT_SECONDS)
        assert len(provider.requests) == 1
        with SessionLocal() as verification:
            messages = tuple(
                verification.scalars(
                    select(WhatsAppMessage).where(
                        WhatsAppMessage.broadcast_recipient_id == ready.recipient_ids[0]
                    )
                )
            )
            assert len(messages) == 1
            assert messages[0].id == message_id
            assert messages[0].client_generated_id == client_id

        with SessionLocal.begin() as session:
            message = session.get(WhatsAppMessage, message_id)
            recipient = session.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            broadcast = session.get(WhatsAppBroadcast, ready.broadcast_id)
            assert message is not None
            assert recipient is not None
            assert broadcast is not None
            message.external_message_id = None
            message.dispatch_state = WhatsAppDispatchState.IN_PROGRESS
            message.provider_state = None
            message.provider_status_at = None
            message.accepted_at = None
            message.sent_at = None
            recipient.status = WhatsAppBroadcastRecipientStatus.IN_PROGRESS
            recipient.claim_token = uuid4()
            recipient.claimed_at = NOW - timedelta(hours=1)
            broadcast.status = WhatsAppBroadcastStatus.PROCESSING

        with SessionLocal() as session:
            _broadcast_service(session, provider, storage).process_batch(
                ready.broadcast_id,
                command_id=uuid4(),
                actor_user_id=ready.context.user_id,
                now=NOW,
            )
        assert len(provider.requests) == 1
        with SessionLocal() as verification:
            message = verification.get(WhatsAppMessage, message_id)
            recipient = verification.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            assert message is not None
            assert recipient is not None
            assert message.dispatch_state is WhatsAppDispatchState.UNKNOWN
            assert recipient.status is WhatsAppBroadcastRecipientStatus.UNKNOWN
    finally:
        _cleanup(ready.context)


def test_claim_transaction_failure_rolls_back_every_claim_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = _ready_broadcast(1)
    provider = FakeWhatsAppProvider(now=NOW, templates=(TEMPLATE,))
    storage = FakeMediaStorage()
    original = WhatsAppBroadcastService._pending_broadcast_message

    def fail_after_message(
        self: WhatsAppBroadcastService,
        broadcast: WhatsAppBroadcast,
        recipient: WhatsAppBroadcastRecipient,
        previous: WhatsAppMessage | None,
        *,
        actor_user_id: int,
        client_generated_id: UUID,
    ) -> WhatsAppMessage:
        original(
            self,
            broadcast,
            recipient,
            previous,
            actor_user_id=actor_user_id,
            client_generated_id=client_generated_id,
        )
        raise RuntimeError("Injected claim failure")

    monkeypatch.setattr(
        WhatsAppBroadcastService,
        "_pending_broadcast_message",
        fail_after_message,
    )
    try:
        with (
            pytest.raises(RuntimeError, match="Injected claim failure"),
            SessionLocal() as session,
        ):
            _broadcast_service(session, provider, storage).process_batch(
                ready.broadcast_id,
                command_id=uuid4(),
                actor_user_id=ready.context.user_id,
                now=NOW,
            )
        with SessionLocal() as verification:
            recipient = verification.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            assert recipient is not None
            assert recipient.status is WhatsAppBroadcastRecipientStatus.READY
            assert recipient.claim_token is None
            assert recipient.conversation_id is None
            assert (
                verification.scalar(
                    select(func.count(WhatsAppMessage.id)).where(
                        WhatsAppMessage.broadcast_recipient_id == recipient.id
                    )
                )
                == 0
            )
            assert len(provider.requests) == 0
    finally:
        _cleanup(ready.context)


def test_dispatch_start_and_reconciliation_failures_rollback_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = _ready_broadcast(1)
    message_id, client_id = _seed_claimed_message(ready, dispatch_started=False)
    provider = FakeWhatsAppProvider(now=NOW, templates=(TEMPLATE,))
    try:
        original_build = WhatsAppMessageService._build_provider_request

        def fail_build(
            self: WhatsAppMessageService,
            message: WhatsAppMessage,
        ) -> SendTemplateRequest:
            del self, message
            raise RuntimeError("Injected dispatch-start failure")

        monkeypatch.setattr(
            WhatsAppMessageService,
            "_build_provider_request",
            fail_build,
        )
        with (
            pytest.raises(RuntimeError, match="Injected dispatch-start failure"),
            SessionLocal() as session,
        ):
            WhatsAppMessageService(session, provider).send(
                _broadcast_message_input(ready, client_id),
                now=NOW,
            )
        with SessionLocal() as verification:
            message = verification.get(WhatsAppMessage, message_id)
            recipient = verification.get(
                WhatsAppBroadcastRecipient,
                ready.recipient_ids[0],
            )
            assert message is not None
            assert recipient is not None
            assert message.dispatch_state is WhatsAppDispatchState.PENDING
            assert recipient.status is WhatsAppBroadcastRecipientStatus.IN_PROGRESS
            assert len(provider.requests) == 0

        monkeypatch.setattr(
            WhatsAppMessageService,
            "_build_provider_request",
            original_build,
        )
        original_recompute = WhatsAppMessageService._recompute_broadcast_recipient

        def fail_recompute(
            self: WhatsAppMessageService,
            recipient: WhatsAppBroadcastRecipient | None,
            *,
            now: datetime,
        ) -> None:
            del self, recipient, now
            raise RuntimeError("Injected reconciliation failure")

        monkeypatch.setattr(
            WhatsAppMessageService,
            "_recompute_broadcast_recipient",
            fail_recompute,
        )
        with (
            pytest.raises(RuntimeError, match="Injected reconciliation failure"),
            SessionLocal() as session,
        ):
            WhatsAppMessageService(session, provider).send(
                _broadcast_message_input(ready, client_id),
                now=NOW,
            )
        assert len(provider.requests) == 1
        with SessionLocal() as verification:
            message = verification.get(WhatsAppMessage, message_id)
            assert message is not None
            assert message.dispatch_state is WhatsAppDispatchState.IN_PROGRESS
            assert message.external_message_id is None

        monkeypatch.setattr(
            WhatsAppMessageService,
            "_recompute_broadcast_recipient",
            original_recompute,
        )
        with SessionLocal() as session:
            replay = WhatsAppMessageService(session, provider).send(
                _broadcast_message_input(ready, client_id),
                now=NOW,
            )
        assert replay.created is False
        assert replay.dispatch_state is WhatsAppDispatchState.IN_PROGRESS
        assert len(provider.requests) == 1
    finally:
        _cleanup(ready.context)


def _persist_identities(customer_count: int) -> PersistedContext:
    suffix = uuid4().hex
    phone_seed = int(suffix[:8], 16) % 90_000_000 + 10_000_000
    with SessionLocal.begin() as session:
        user = User(
            full_name="CRM-013 concurrency",
            email=f"crm-013-{suffix}@faa.test",
            password_hash=hash_password("crm-013-test-password"),
            role=UserRole.SUPERVISOR,
        )
        session.add(user)
        session.flush()
        customers = tuple(
            Customer(
                name=f"CRM-013 customer {index} {suffix}",
                phone=f"+54 9 11 {phone_seed + index}",
            )
            for index in range(customer_count)
        )
        session.add_all(customers)
        session.flush()
        return PersistedContext(user.id, tuple(customer.id for customer in customers))


def _ready_broadcast(
    customer_count: int,
    *,
    start: bool = True,
    existing_context: PersistedContext | None = None,
) -> ReadyBroadcast:
    context = existing_context or _persist_identities(customer_count)
    if len(context.customer_ids) != customer_count:
        raise ValueError("Existing context has an unexpected Customer count")
    provider = FakeWhatsAppProvider(now=NOW, templates=(TEMPLATE,))
    storage = FakeMediaStorage()
    for customer_id in context.customer_ids:
        with SessionLocal() as session:
            WhatsAppConsentService(session).append(
                _consent_input(
                    uuid4(),
                    customer_id,
                    context.user_id,
                    WhatsAppConsentDecision.OPT_IN,
                ),
                now=NOW,
            )
    with SessionLocal() as session:
        service = _broadcast_service(session, provider, storage)
        broadcast, _created = service.create(
            _broadcast_create_input(uuid4(), context.user_id, "Ready"),
            now=NOW,
        )
        selection = service.replace_recipients(
            broadcast.id,
            command_id=uuid4(),
            customer_ids=context.customer_ids,
            expected_version=broadcast.version,
            actor_user_id=context.user_id,
            now=NOW,
        )
        validation = service.validate(
            broadcast.id,
            expected_version=selection.version,
            actor_user_id=context.user_id,
            now=NOW,
        )
        assert validation.validation_token is not None
        service.confirm(
            broadcast.id,
            command_id=uuid4(),
            expected_version=selection.version,
            validation_token=validation.validation_token,
            actor_user_id=context.user_id,
            now=NOW,
        )
        if start:
            service.start(
                broadcast.id,
                command_id=uuid4(),
                actor_user_id=context.user_id,
                now=NOW,
            )
        broadcast_id = broadcast.id
    with SessionLocal() as verification:
        recipient_ids = tuple(
            verification.scalars(
                select(WhatsAppBroadcastRecipient.id)
                .where(WhatsAppBroadcastRecipient.broadcast_id == broadcast_id)
                .order_by(WhatsAppBroadcastRecipient.id)
            )
        )
    return ReadyBroadcast(
        PersistedContext(
            context.user_id,
            context.customer_ids,
            (*context.broadcast_ids, broadcast_id),
        ),
        broadcast_id,
        recipient_ids,
    )


def _persist_conversation(customer_id: int) -> int:
    with SessionLocal.begin() as session:
        customer = session.get(Customer, customer_id)
        assert customer is not None
        assert customer.phone is not None
        conversation = WhatsAppConversation(
            customer_id=customer.id,
            external_phone=customer.phone,
            phone_match_key=customer.phone.replace(" ", ""),
            display_name=customer.name,
            resolution_status=WhatsAppConversationResolution.RESOLVED,
            last_inbound_at=NOW,
        )
        session.add(conversation)
        session.flush()
        return conversation.id


def _seed_claimed_message(
    ready: ReadyBroadcast,
    *,
    dispatch_started: bool,
) -> tuple[int, UUID]:
    client_id = uuid4()
    with SessionLocal.begin() as session:
        recipient = session.get(
            WhatsAppBroadcastRecipient,
            ready.recipient_ids[0],
        )
        assert recipient is not None
        customer = session.get(Customer, recipient.customer_id)
        assert customer is not None
        conversation = WhatsAppConversation(
            customer_id=customer.id,
            external_phone=recipient.normalized_phone,
            phone_match_key=recipient.normalized_phone,
            display_name=recipient.customer_display_name,
            resolution_status=WhatsAppConversationResolution.RESOLVED,
        )
        session.add(conversation)
        session.flush()
        recipient.conversation_id = conversation.id
        recipient.status = WhatsAppBroadcastRecipientStatus.IN_PROGRESS
        recipient.claim_token = uuid4()
        recipient.claimed_at = NOW - timedelta(hours=1)
        message = WhatsAppMessage(
            conversation_id=conversation.id,
            client_generated_id=client_id,
            direction=WhatsAppDirection.OUTBOUND,
            message_type=WhatsAppMessageType.TEXT,
            origin=WhatsAppMessageOrigin.BROADCAST,
            sent_by_user_id=ready.context.user_id,
            broadcast_recipient_id=recipient.id,
            template_name=TEMPLATE.name,
            template_language=TEMPLATE.language,
            dispatch_state=(
                WhatsAppDispatchState.IN_PROGRESS
                if dispatch_started
                else WhatsAppDispatchState.PENDING
            ),
        )
        session.add(message)
        session.flush()
        return message.id, client_id


def _consent_input(
    event_id: UUID,
    customer_id: int,
    user_id: int,
    decision: WhatsAppConsentDecision,
) -> ConsentEventInput:
    return ConsentEventInput(
        client_event_id=event_id,
        customer_id=customer_id,
        decision=decision,
        source=WhatsAppConsentSource.FAA_CRM,
        occurred_at=NOW - timedelta(seconds=1),
        effective_at=None,
        evidence_reference=None,
        recorded_by_user_id=user_id,
    )


def _broadcast_create_input(
    client_id: UUID,
    user_id: int,
    label: str,
) -> BroadcastCreateInput:
    return BroadcastCreateInput(
        client_generated_id=client_id,
        label=label,
        external_campaign_reference=None,
        template_external_id=TEMPLATE.external_id,
        parameters=(),
        header_media_ref=None,
        created_by_user_id=user_id,
    )


def _human_message_input(
    conversation_id: int,
    user_id: int,
    client_id: UUID,
    body: str,
) -> OutboundMessageInput:
    return OutboundMessageInput(
        conversation_id=conversation_id,
        client_generated_id=client_id,
        sent_by_user_id=user_id,
        message_type=WhatsAppMessageType.TEXT,
        body=body,
    )


def _broadcast_message_input(
    ready: ReadyBroadcast,
    client_id: UUID,
) -> OutboundMessageInput:
    with SessionLocal() as session:
        recipient = session.get(
            WhatsAppBroadcastRecipient,
            ready.recipient_ids[0],
        )
        assert recipient is not None
        assert recipient.conversation_id is not None
        conversation_id = recipient.conversation_id
    return OutboundMessageInput(
        conversation_id=conversation_id,
        client_generated_id=client_id,
        sent_by_user_id=ready.context.user_id,
        message_type=WhatsAppMessageType.TEXT,
        body=None,
        origin=WhatsAppMessageOrigin.BROADCAST,
        broadcast_recipient_id=ready.recipient_ids[0],
        template_name=TEMPLATE.name,
        template_language=TEMPLATE.language,
    )


def _broadcast_service(
    session: Session,
    provider: FakeWhatsAppProvider,
    storage: FakeMediaStorage,
    *,
    batch_size: int = 20,
) -> WhatsAppBroadcastService:
    return WhatsAppBroadcastService(
        session,
        provider,
        storage,
        batch_size=batch_size,
        claim_timeout=timedelta(minutes=5),
    )


def _cleanup(context: PersistedContext) -> None:
    with SessionLocal.begin() as session:
        session.execute(text("SET LOCAL session_replication_role = replica"))
        recipient_ids = select(WhatsAppBroadcastRecipient.id).where(
            WhatsAppBroadcastRecipient.broadcast_id.in_(context.broadcast_ids)
        )
        message_ids = select(WhatsAppMessage.id).where(
            WhatsAppMessage.broadcast_recipient_id.in_(recipient_ids)
            | WhatsAppMessage.conversation_id.in_(
                select(WhatsAppConversation.id).where(
                    WhatsAppConversation.customer_id.in_(context.customer_ids)
                )
            )
        )
        external_ids = select(WhatsAppMessage.external_message_id).where(
            WhatsAppMessage.id.in_(message_ids),
            WhatsAppMessage.external_message_id.is_not(None),
        )
        session.execute(
            delete(WhatsAppMessageStatusEvent).where(
                WhatsAppMessageStatusEvent.message_id.in_(message_ids)
                | WhatsAppMessageStatusEvent.external_message_id.in_(external_ids)
            )
        )
        session.execute(
            delete(WhatsAppBroadcastAuditEvent).where(
                WhatsAppBroadcastAuditEvent.broadcast_id.in_(context.broadcast_ids)
            )
        )
        session.execute(
            delete(WhatsAppAttachment).where(
                WhatsAppAttachment.message_id.in_(message_ids)
            )
        )
        session.execute(
            delete(WhatsAppMessage).where(WhatsAppMessage.id.in_(message_ids))
        )
        session.execute(
            delete(WhatsAppBroadcastRecipient).where(
                WhatsAppBroadcastRecipient.id.in_(recipient_ids)
            )
        )
        session.execute(
            delete(WhatsAppBroadcastTemplateParameter).where(
                WhatsAppBroadcastTemplateParameter.broadcast_id.in_(
                    context.broadcast_ids
                )
            )
        )
        session.execute(
            delete(WhatsAppBroadcast).where(
                WhatsAppBroadcast.id.in_(context.broadcast_ids)
            )
        )
        session.execute(
            delete(WhatsAppMarketingConsentEvent).where(
                WhatsAppMarketingConsentEvent.customer_id.in_(context.customer_ids)
            )
        )
        session.execute(
            delete(WhatsAppConversation).where(
                WhatsAppConversation.customer_id.in_(context.customer_ids)
            )
        )
        session.execute(delete(Customer).where(Customer.id.in_(context.customer_ids)))
        session.execute(delete(User).where(User.id == context.user_id))
