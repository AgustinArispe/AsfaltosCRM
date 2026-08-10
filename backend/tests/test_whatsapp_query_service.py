from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, dataclass, field
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityStatus,
    User,
    WhatsAppAttachment,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppMessageStatusEvent,
    WhatsAppMessageType,
    WhatsAppOpportunityLinkSource,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services import (
    ChangePageRequest,
    ConversationListFilters,
    ConversationPageRequest,
    ConversationQueryService,
    CursorRejectionMeasurement,
    EntityNotFoundError,
    MessagePageRequest,
    MessageQueryService,
    PollingQueryService,
    RecordingWhatsAppQueryMetrics,
    ResourceChangeCursor,
    WhatsAppCursorKind,
    WhatsAppCursorRejectionReason,
    WhatsAppQueryMetricName,
    WhatsAppQueryOperation,
    WhatsAppQueryOutcome,
)

_BASE_TIME = datetime(2026, 1, 5, 12, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class SeededInbox:
    primary_customer: Customer
    primary_conversation: WhatsAppConversation
    secondary_conversation: WhatsAppConversation
    unresolved_conversation: WhatsAppConversation
    active_opportunity: Opportunity
    other_open_opportunity: Opportunity
    terminal_opportunity: Opportunity
    inbound_message: WhatsAppMessage
    outbound_message: WhatsAppMessage
    retry_message: WhatsAppMessage


@dataclass(slots=True)
class StatementCounter:
    count: int = 0
    statements: list[str] = field(default_factory=list)


@pytest.fixture
def seeded_inbox(db_session: Session, supervisor_user: User) -> SeededInbox:
    primary_customer = Customer(
        name="Constructora Alpha",
        company="Alpha Vial",
        phone="+54 (11) 4444-1000",
        province="Buenos Aires",
        created_at=_BASE_TIME,
        updated_at=_BASE_TIME,
    )
    secondary_customer = Customer(
        name="Hormigones Beta",
        company="Beta Obras",
        phone="+54 11 4444-2000",
        created_at=_BASE_TIME,
        updated_at=_BASE_TIME,
    )
    db_session.add_all((primary_customer, secondary_customer))
    db_session.flush()

    active_opportunity = _opportunity(
        primary_customer.id,
        OpportunityStatus.NEGOCIACION,
        _BASE_TIME + timedelta(minutes=1),
    )
    other_open_opportunity = _opportunity(
        primary_customer.id,
        OpportunityStatus.NUEVA,
        _BASE_TIME + timedelta(minutes=2),
    )
    terminal_opportunity = _opportunity(
        primary_customer.id,
        OpportunityStatus.GANADA,
        _BASE_TIME + timedelta(minutes=3),
    )
    db_session.add_all(
        (active_opportunity, other_open_opportunity, terminal_opportunity)
    )
    db_session.flush()

    primary_conversation = _conversation(
        primary_customer.id,
        "+54 11 4444-1000",
        "+541144441000",
        display_name="Compras Alpha",
        waiting=True,
        unread=4,
        last_message_at=_BASE_TIME + timedelta(minutes=20),
        updated_at=_BASE_TIME + timedelta(minutes=20),
    )
    secondary_conversation = _conversation(
        secondary_customer.id,
        "+54 11 4444-2000",
        "+541144442000",
        display_name="Beta",
        waiting=True,
        unread=2,
        last_message_at=_BASE_TIME + timedelta(minutes=20),
        updated_at=_BASE_TIME + timedelta(minutes=20),
    )
    quiet_conversation = _conversation(
        primary_customer.id,
        "+54 11 4444-3000",
        "+541144443000",
        display_name="Alpha depósito",
        waiting=False,
        unread=5,
        last_message_at=_BASE_TIME + timedelta(minutes=21),
        updated_at=_BASE_TIME + timedelta(minutes=21),
    )
    unresolved_conversation = _conversation(
        None,
        "+54 11 4444-9000",
        "+541144449000",
        display_name="Contacto por revisar",
        waiting=False,
        unread=0,
        last_message_at=None,
        updated_at=_BASE_TIME + timedelta(minutes=4),
        resolution=WhatsAppConversationResolution.NEEDS_REVIEW,
    )
    db_session.add_all(
        (
            primary_conversation,
            secondary_conversation,
            quiet_conversation,
            unresolved_conversation,
        )
    )
    db_session.flush()

    historical_link = WhatsAppConversationOpportunity(
        conversation_id=primary_conversation.id,
        opportunity_id=terminal_opportunity.id,
        linked_at=_BASE_TIME + timedelta(minutes=4),
        unlinked_at=_BASE_TIME + timedelta(minutes=5),
        linked_by_user_id=supervisor_user.id,
        link_source=WhatsAppOpportunityLinkSource.MANUAL,
    )
    active_link = WhatsAppConversationOpportunity(
        conversation_id=primary_conversation.id,
        opportunity_id=active_opportunity.id,
        linked_at=_BASE_TIME + timedelta(minutes=6),
        linked_by_user_id=supervisor_user.id,
        link_source=WhatsAppOpportunityLinkSource.MANUAL,
    )
    db_session.add_all((historical_link, active_link))
    db_session.flush()

    inbound_message = WhatsAppMessage(
        conversation_id=primary_conversation.id,
        external_message_id="wamid.query.inbound",
        direction=WhatsAppDirection.INBOUND,
        message_type=WhatsAppMessageType.TEXT,
        body="Necesito emulsión",
        provider_state=WhatsAppProviderState.RECEIVED,
        provider_message_at=_BASE_TIME + timedelta(minutes=7),
        created_at=_BASE_TIME + timedelta(minutes=7),
        updated_at=_BASE_TIME + timedelta(minutes=7),
    )
    outbound_message = WhatsAppMessage(
        conversation_id=primary_conversation.id,
        external_message_id="wamid.query.outbound",
        client_generated_id=UUID("00000000-0000-0000-0000-000000000101"),
        direction=WhatsAppDirection.OUTBOUND,
        message_type=WhatsAppMessageType.DOCUMENT,
        body="Cotización adjunta",
        sent_by_user_id=supervisor_user.id,
        dispatch_state=WhatsAppDispatchState.ACCEPTED,
        provider_state=WhatsAppProviderState.READ,
        accepted_at=_BASE_TIME + timedelta(minutes=8),
        sent_at=_BASE_TIME + timedelta(minutes=8),
        delivered_at=_BASE_TIME + timedelta(minutes=9),
        read_at=_BASE_TIME + timedelta(minutes=10),
        provider_status_at=_BASE_TIME + timedelta(minutes=10),
        created_at=_BASE_TIME + timedelta(minutes=8),
        updated_at=_BASE_TIME + timedelta(minutes=10),
    )
    db_session.add_all((inbound_message, outbound_message))
    db_session.flush()
    retry_message = WhatsAppMessage(
        conversation_id=primary_conversation.id,
        client_generated_id=UUID("00000000-0000-0000-0000-000000000102"),
        direction=WhatsAppDirection.OUTBOUND,
        message_type=WhatsAppMessageType.IMAGE,
        body=None,
        sent_by_user_id=supervisor_user.id,
        retry_of_message_id=outbound_message.id,
        dispatch_state=WhatsAppDispatchState.UNKNOWN,
        provider_error_code="provider_timeout",
        provider_error_message="Acceptance could not be confirmed",
        created_at=_BASE_TIME + timedelta(minutes=11),
        updated_at=_BASE_TIME + timedelta(minutes=11),
    )
    db_session.add(retry_message)
    db_session.flush()
    db_session.add_all(
        (
            WhatsAppAttachment(
                message_id=outbound_message.id,
                media_type=WhatsAppMessageType.DOCUMENT,
                mime_type="application/pdf",
                filename="../cotizacion.pdf",
                size_bytes=4_096,
                storage_key="private/query/cotizacion.pdf",
                storage_status=WhatsAppStorageStatus.AVAILABLE,
                created_at=_BASE_TIME + timedelta(minutes=8),
                updated_at=_BASE_TIME + timedelta(minutes=9),
            ),
            WhatsAppAttachment(
                message_id=retry_message.id,
                media_type=WhatsAppMessageType.IMAGE,
                mime_type="image/jpeg",
                filename="foto.jpg",
                size_bytes=None,
                storage_status=WhatsAppStorageStatus.PENDING,
                created_at=_BASE_TIME + timedelta(minutes=11),
                updated_at=_BASE_TIME + timedelta(minutes=11),
            ),
            WhatsAppMessageStatusEvent(
                message_id=outbound_message.id,
                external_message_id="wamid.query.outbound",
                provider_state=WhatsAppProviderState.READ,
                occurred_at=_BASE_TIME + timedelta(minutes=10),
                received_at=_BASE_TIME + timedelta(minutes=12),
            ),
        )
    )
    db_session.commit()
    return SeededInbox(
        primary_customer=primary_customer,
        primary_conversation=primary_conversation,
        secondary_conversation=secondary_conversation,
        unresolved_conversation=unresolved_conversation,
        active_opportunity=active_opportunity,
        other_open_opportunity=other_open_opportunity,
        terminal_opportunity=terminal_opportunity,
        inbound_message=inbound_message,
        outbound_message=outbound_message,
        retry_message=retry_message,
    )


def test_conversation_list_returns_immutable_filtered_keyset_pages(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    service = ConversationQueryService(db_session)
    snapshot = _BASE_TIME + timedelta(hours=1)

    first = service.list_conversations(
        ConversationListFilters(waiting_only=True),
        ConversationPageRequest(limit=1),
        snapshot_at=snapshot,
    )
    second = service.list_conversations(
        ConversationListFilters(waiting_only=True),
        ConversationPageRequest(limit=1, cursor=first.next_cursor),
    )

    assert [item.id for item in first.items] == [seeded_inbox.primary_conversation.id]
    assert [item.id for item in second.items] == [
        seeded_inbox.secondary_conversation.id
    ]
    assert first.next_cursor is not None
    assert second.next_cursor is None
    assert first.sync_cursor.resource_updated_at == snapshot
    with pytest.raises(FrozenInstanceError):
        _attempt_mutation(first.items[0])

    unread = service.list_conversations(
        ConversationListFilters(unread_only=True),
        ConversationPageRequest(),
        snapshot_at=snapshot,
    )
    assert all(item.unread_count > 0 for item in unread.items)
    assert [item.waiting_for_response for item in unread.items[:2]] == [True, True]


@pytest.mark.parametrize(
    ("search", "expected_display_name"),
    [
        ("  alpha vial  ", "Compras Alpha"),
        ("+54 (11) 4444-2000", "Beta"),
        ("por revisar", "Contacto por revisar"),
    ],
)
def test_conversation_search_is_trimmed_and_conservative(
    db_session: Session,
    seeded_inbox: SeededInbox,
    search: str,
    expected_display_name: str,
) -> None:
    del seeded_inbox
    result = ConversationQueryService(db_session).list_conversations(
        ConversationListFilters(search=search),
        ConversationPageRequest(),
        snapshot_at=_BASE_TIME + timedelta(hours=1),
    )

    assert expected_display_name in {item.display_name for item in result.items}


def test_conversation_detail_has_links_suggestions_and_no_messages(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    metrics = RecordingWhatsAppQueryMetrics()
    detail = ConversationQueryService(db_session, metrics).get_conversation_detail(
        seeded_inbox.primary_conversation.id
    )

    assert detail.summary.customer is not None
    assert detail.summary.customer.name == "Constructora Alpha"
    assert detail.summary.active_opportunity is not None
    assert detail.summary.active_opportunity.id == seeded_inbox.active_opportunity.id
    assert {item.id for item in detail.summary.opportunity_suggestions} == {
        seeded_inbox.active_opportunity.id,
        seeded_inbox.other_open_opportunity.id,
    }
    assert [link.opportunity.id for link in detail.opportunity_links] == [
        seeded_inbox.terminal_opportunity.id,
        seeded_inbox.active_opportunity.id,
    ]
    assert detail.opportunity_links[0].is_active is False
    assert detail.opportunity_links[1].is_actionable is True
    assert not hasattr(detail, "messages")
    assert metrics.queries[-1].db_statements == 3


def test_unresolved_conversation_preserves_nullable_identity(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    detail = ConversationQueryService(db_session).get_conversation_detail(
        seeded_inbox.unresolved_conversation.id
    )

    assert detail.summary.customer is None
    assert (
        detail.summary.resolution_status is WhatsAppConversationResolution.NEEDS_REVIEW
    )
    assert detail.summary.opportunity_suggestions == ()


def test_soft_deleted_relations_are_historical_and_not_actionable(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    deleted_at = _BASE_TIME + timedelta(minutes=40)
    seeded_inbox.primary_customer.deleted_at = deleted_at
    seeded_inbox.primary_customer.updated_at = deleted_at
    seeded_inbox.active_opportunity.deleted_at = deleted_at
    seeded_inbox.active_opportunity.updated_at = deleted_at
    db_session.commit()

    detail = ConversationQueryService(db_session).get_conversation_detail(
        seeded_inbox.primary_conversation.id
    )

    assert detail.summary.customer is not None
    assert detail.summary.customer.is_available is False
    assert detail.summary.opportunity_suggestions == ()
    assert detail.summary.active_opportunity is not None
    assert detail.summary.active_opportunity.is_available is False
    active_link = next(link for link in detail.opportunity_links if link.is_active)
    assert active_link.is_actionable is False


def test_missing_conversation_records_safe_not_found_metric(
    db_session: Session,
) -> None:
    metrics = RecordingWhatsAppQueryMetrics()
    with pytest.raises(EntityNotFoundError):
        ConversationQueryService(db_session, metrics).get_conversation_detail(999_999)

    assert metrics.queries[-1].outcome is WhatsAppQueryOutcome.ERROR
    assert metrics.errors[-1].category.value == "not_found"


def test_message_history_pages_chronologically_with_safe_attachments(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    service = MessageQueryService(db_session)
    first = service.list_message_history(
        seeded_inbox.primary_conversation.id,
        MessagePageRequest(limit=2),
        snapshot_at=_BASE_TIME + timedelta(hours=1),
    )
    second = service.list_message_history(
        seeded_inbox.primary_conversation.id,
        MessagePageRequest(limit=2, before=first.next_before_cursor),
    )

    assert [item.id for item in first.items] == [
        seeded_inbox.outbound_message.id,
        seeded_inbox.retry_message.id,
    ]
    assert [item.id for item in second.items] == [seeded_inbox.inbound_message.id]
    assert first.next_before_cursor is not None
    assert second.next_before_cursor is None
    document = first.items[0]
    assert document.attachment is not None
    assert document.attachment.filename == "cotizacion.pdf"
    assert document.attachment.content_reference is not None
    assert not hasattr(document.attachment, "storage_key")
    assert not hasattr(document.attachment, "provider_media_id")
    assert document.status.provider_state is WhatsAppProviderState.READ
    retry = first.items[1]
    assert retry.is_retry is True
    assert retry.retry_of_message_id == seeded_inbox.outbound_message.id
    assert retry.status.dispatch_state is WhatsAppDispatchState.UNKNOWN
    assert retry.attachment is not None
    assert retry.attachment.content_reference is None


def test_message_history_equal_timestamp_uses_id_tie_breaker(
    db_session: Session,
    seeded_inbox: SeededInbox,
    supervisor_user: User,
) -> None:
    same_time = _BASE_TIME + timedelta(minutes=30)
    messages = [
        WhatsAppMessage(
            conversation_id=seeded_inbox.secondary_conversation.id,
            client_generated_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
            direction=WhatsAppDirection.OUTBOUND,
            message_type=WhatsAppMessageType.TEXT,
            body=f"Mensaje {index}",
            sent_by_user_id=supervisor_user.id,
            dispatch_state=WhatsAppDispatchState.PENDING,
            created_at=same_time,
            updated_at=same_time,
        )
        for index in range(201, 204)
    ]
    db_session.add_all(messages)
    db_session.commit()
    service = MessageQueryService(db_session)

    first = service.list_message_history(
        seeded_inbox.secondary_conversation.id,
        MessagePageRequest(limit=2),
        snapshot_at=_BASE_TIME + timedelta(hours=1),
    )
    second = service.list_message_history(
        seeded_inbox.secondary_conversation.id,
        MessagePageRequest(limit=2, before=first.next_before_cursor),
    )

    assert [item.id for item in first.items] == [messages[1].id, messages[2].id]
    assert [item.id for item in second.items] == [messages[0].id]


def test_polling_uses_related_change_keys_and_retains_empty_cursor(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    cursor = ResourceChangeCursor(
        _BASE_TIME + timedelta(minutes=25),
        seeded_inbox.primary_conversation.id,
    )
    seeded_inbox.primary_customer.updated_at = _BASE_TIME + timedelta(minutes=30)
    seeded_inbox.other_open_opportunity.updated_at = _BASE_TIME + timedelta(minutes=31)
    db_session.commit()

    service = PollingQueryService(db_session)
    changes = service.list_conversation_changes(ChangePageRequest(cursor, limit=1))

    assert changes.items
    assert changes.has_more is True
    assert changes.next_cursor != cursor
    remaining = service.list_conversation_changes(
        ChangePageRequest(changes.next_cursor, limit=10)
    )
    changed_ids = {item.id for item in (*changes.items, *remaining.items)}
    assert seeded_inbox.primary_conversation.id in changed_ids

    active_link = db_session.scalar(
        select(WhatsAppConversationOpportunity).where(
            WhatsAppConversationOpportunity.conversation_id
            == seeded_inbox.primary_conversation.id,
            WhatsAppConversationOpportunity.unlinked_at.is_(None),
        )
    )
    assert active_link is not None
    active_link.unlinked_at = _BASE_TIME + timedelta(minutes=40)
    db_session.commit()
    link_changes = service.list_conversation_changes(
        ChangePageRequest(ResourceChangeCursor(_BASE_TIME + timedelta(minutes=35), 0))
    )
    assert seeded_inbox.primary_conversation.id in {
        item.id for item in link_changes.items
    }

    empty_cursor = ResourceChangeCursor(
        _BASE_TIME + timedelta(days=10),
        9_223_372_036_854_775_807,
    )
    empty = service.list_conversation_changes(ChangePageRequest(empty_cursor))
    assert empty.items == ()
    assert empty.next_cursor == empty_cursor


def test_message_polling_includes_attachment_and_status_updates(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    cursor = ResourceChangeCursor(_BASE_TIME + timedelta(minutes=10), 0)
    result = PollingQueryService(db_session).list_message_changes(
        seeded_inbox.primary_conversation.id,
        ChangePageRequest(cursor),
    )

    changed_ids = {item.id for item in result.items}
    assert seeded_inbox.outbound_message.id in changed_ids
    assert seeded_inbox.retry_message.id in changed_ids
    outbound = next(
        item for item in result.items if item.id == seeded_inbox.outbound_message.id
    )
    assert outbound.resource_updated_at == _BASE_TIME + timedelta(minutes=12)
    assert outbound.status.provider_state is WhatsAppProviderState.READ


def test_queries_do_not_recompute_or_mutate_persisted_projections(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    before = (
        seeded_inbox.primary_conversation.unread_count,
        seeded_inbox.primary_conversation.waiting_for_response,
        seeded_inbox.primary_conversation.waiting_since_at,
    )
    result = ConversationQueryService(db_session).list_conversations(
        ConversationListFilters(),
        ConversationPageRequest(),
        snapshot_at=_BASE_TIME + timedelta(hours=1),
    )

    assert result.items
    db_session.refresh(seeded_inbox.primary_conversation)
    assert (
        seeded_inbox.primary_conversation.unread_count,
        seeded_inbox.primary_conversation.waiting_for_response,
        seeded_inbox.primary_conversation.waiting_since_at,
    ) == before
    assert not db_session.dirty


def test_query_statement_counts_are_bounded_and_metrics_are_safe(
    db_session: Session,
    seeded_inbox: SeededInbox,
) -> None:
    metrics = RecordingWhatsAppQueryMetrics()
    conversations = ConversationQueryService(db_session, metrics)
    messages = MessageQueryService(db_session, metrics)

    with _statement_counter(db_session) as first_counter:
        conversations.list_conversations(
            ConversationListFilters(),
            ConversationPageRequest(limit=1),
            snapshot_at=_BASE_TIME + timedelta(hours=1),
        )
    one_count = metrics.queries[-1].db_statements
    with _statement_counter(db_session) as many_counter:
        conversations.list_conversations(
            ConversationListFilters(),
            ConversationPageRequest(limit=50),
            snapshot_at=_BASE_TIME + timedelta(hours=1),
        )
    many_count = metrics.queries[-1].db_statements
    with _statement_counter(db_session) as message_counter:
        messages.list_message_history(
            seeded_inbox.primary_conversation.id,
            MessagePageRequest(),
            snapshot_at=_BASE_TIME + timedelta(hours=1),
        )

    assert one_count == many_count == 3
    assert first_counter.count == many_counter.count == 3, first_counter.statements
    assert metrics.queries[-1].db_statements == 2
    assert message_counter.count == 2
    assert {item.operation for item in metrics.queries} == {
        WhatsAppQueryOperation.CONVERSATION_LIST,
        WhatsAppQueryOperation.MESSAGE_HISTORY,
    }
    metrics.record_cursor_rejection(
        CursorRejectionMeasurement(
            WhatsAppCursorKind.MESSAGE_PAGE,
            WhatsAppCursorRejectionReason.MALFORMED,
        )
    )
    assert metrics.cursor_rejections[-1].reason.value == "malformed"
    assert not hasattr(metrics.queries[-1], "phone")
    assert not hasattr(metrics.queries[-1], "message_body")
    assert metrics.queries[-1].metric_names == (
        WhatsAppQueryMetricName.DURATION_SECONDS,
        WhatsAppQueryMetricName.ROWS_RETURNED,
        WhatsAppQueryMetricName.DB_STATEMENTS_TOTAL,
    )


@pytest.mark.parametrize(
    "request_factory",
    [
        lambda: ConversationPageRequest(limit=0),
        lambda: ConversationPageRequest(limit=51),
        lambda: MessagePageRequest(limit=0),
        lambda: MessagePageRequest(limit=101),
        lambda: ChangePageRequest(ResourceChangeCursor(_BASE_TIME, 0), limit=501),
    ],
)
def test_page_limits_are_bounded(request_factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        request_factory()


def test_message_history_requires_existing_conversation(db_session: Session) -> None:
    with pytest.raises(EntityNotFoundError):
        MessageQueryService(db_session).list_message_history(
            999_999,
            MessagePageRequest(),
        )


def test_query_performance_targets_with_bounded_faa_dataset(
    db_session: Session,
    supervisor_user: User,
) -> None:
    customer = Customer(
        name="Cliente benchmark",
        phone="+54 11 5555-0000",
        created_at=_BASE_TIME,
        updated_at=_BASE_TIME,
    )
    db_session.add(customer)
    db_session.flush()
    conversations: list[WhatsAppConversation] = []
    for index in range(80):
        conversation = _conversation(
            customer.id,
            f"+54 11 5555-{index:04d}",
            f"+54115555{index:04d}",
            display_name=f"Benchmark {index}",
            waiting=index % 2 == 0,
            unread=index % 7,
            last_message_at=_BASE_TIME + timedelta(seconds=index),
            updated_at=_BASE_TIME + timedelta(seconds=index),
        )
        conversations.append(conversation)
    db_session.add_all(conversations)
    db_session.flush()
    messages: list[WhatsAppMessage] = []
    for index in range(120):
        messages.append(
            WhatsAppMessage(
                conversation_id=conversations[0].id,
                client_generated_id=UUID(f"10000000-0000-0000-0000-{index + 1:012d}"),
                direction=WhatsAppDirection.OUTBOUND,
                message_type=WhatsAppMessageType.TEXT,
                body=f"Benchmark message {index}",
                sent_by_user_id=supervisor_user.id,
                dispatch_state=WhatsAppDispatchState.PENDING,
                created_at=_BASE_TIME + timedelta(seconds=index),
                updated_at=_BASE_TIME + timedelta(seconds=index),
            )
        )
    db_session.add_all(messages)
    db_session.commit()

    conversation_service = ConversationQueryService(db_session)
    message_service = MessageQueryService(db_session)
    polling_service = PollingQueryService(db_session)
    snapshot = _BASE_TIME + timedelta(days=1)
    measurements: dict[str, list[float]] = {
        "conversation_list": [],
        "conversation_detail": [],
        "message_history": [],
        "polling": [],
    }
    for _iteration in range(20):
        measurements["conversation_list"].append(
            _elapsed_ms(
                lambda: conversation_service.list_conversations(
                    ConversationListFilters(),
                    ConversationPageRequest(limit=50),
                    snapshot_at=snapshot,
                )
            )
        )
        measurements["conversation_detail"].append(
            _elapsed_ms(
                lambda: conversation_service.get_conversation_detail(
                    conversations[0].id
                )
            )
        )
        measurements["message_history"].append(
            _elapsed_ms(
                lambda: message_service.list_message_history(
                    conversations[0].id,
                    MessagePageRequest(limit=100),
                    snapshot_at=snapshot,
                )
            )
        )
        measurements["polling"].append(
            _elapsed_ms(
                lambda: polling_service.list_conversation_changes(
                    ChangePageRequest(ResourceChangeCursor(_BASE_TIME, 0))
                )
            )
        )

    p95 = {name: _p95(values) for name, values in measurements.items()}
    print(f"CRM-007 benchmark P95 ms: {p95}")
    assert p95["conversation_list"] <= 250
    assert p95["conversation_detail"] <= 250
    assert p95["message_history"] <= 250
    assert p95["polling"] <= 200


def _conversation(
    customer_id: int | None,
    external_phone: str,
    phone_match_key: str,
    *,
    display_name: str,
    waiting: bool,
    unread: int,
    last_message_at: datetime | None,
    updated_at: datetime,
    resolution: WhatsAppConversationResolution = (
        WhatsAppConversationResolution.RESOLVED
    ),
) -> WhatsAppConversation:
    return WhatsAppConversation(
        customer_id=customer_id,
        external_phone=external_phone,
        phone_match_key=phone_match_key,
        display_name=display_name,
        resolution_status=resolution,
        last_message_at=last_message_at,
        last_inbound_at=last_message_at if waiting else None,
        unread_count=unread,
        waiting_for_response=waiting,
        waiting_since_at=last_message_at if waiting else None,
        window_expires_at=(
            last_message_at + timedelta(hours=24)
            if last_message_at is not None
            else None
        ),
        created_at=_BASE_TIME,
        updated_at=updated_at,
    )


def _opportunity(
    customer_id: int,
    status: OpportunityStatus,
    created_at: datetime,
) -> Opportunity:
    return Opportunity(
        customer_id=customer_id,
        source=LeadSource.WHATSAPP,
        status=status,
        current_status_entered_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )


def _elapsed_ms(operation: Callable[[], object]) -> float:
    started_at = perf_counter()
    operation()
    return (perf_counter() - started_at) * 1_000


def _attempt_mutation(projection: object) -> None:
    projection.__setattr__("unread_count", 0)


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[index]


@contextmanager
def _statement_counter(session: Session) -> Iterator[StatementCounter]:
    counter = StatementCounter()
    bind = session.get_bind()

    def count_statement(
        _connection: object,
        _cursor: object,
        _statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if _statement.lstrip().upper().startswith("SELECT"):
            counter.count += 1
            counter.statements.append(_statement)

    event.listen(bind, "before_cursor_execute", count_statement)
    try:
        yield counter
    finally:
        event.remove(bind, "before_cursor_execute", count_statement)
