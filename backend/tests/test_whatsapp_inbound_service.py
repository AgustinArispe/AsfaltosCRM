from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Opportunity,
    OpportunityStatus,
    OpportunityStatusHistory,
    User,
    WhatsAppAttachment,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppMessage,
    WhatsAppMessageType,
    WhatsAppOpportunityLinkSource,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services import (
    InboundAttachmentInput,
    InboundMessageInput,
    OpportunityService,
    WhatsAppConversationService,
    WhatsAppIdempotencyConflictError,
    WhatsAppInboundService,
    WhatsAppOpportunityAssociationError,
)
from app.services.errors import WhatsAppConversationResolutionError
from app.whatsapp import FakeWhatsAppProvider

NOW = datetime(2030, 8, 10, 15, 0, tzinfo=UTC)


def inbound(
    external_id: str,
    phone: str = "+54 (11) 4444-1234",
    *,
    display_name: str | None = "Cliente WA",
    body: str | None = "Necesito asfalto",
    message_type: WhatsAppMessageType = WhatsAppMessageType.TEXT,
    attachment: InboundAttachmentInput | None = None,
    occurred_at: datetime = NOW,
) -> InboundMessageInput:
    return InboundMessageInput(
        external_message_id=external_id,
        external_phone=phone,
        provider_contact_id="contact-1",
        display_name=display_name,
        message_type=message_type,
        body=body,
        provider_message_at=occurred_at,
        attachment=attachment,
    )


def provider() -> FakeWhatsAppProvider:
    return FakeWhatsAppProvider(now=NOW, freeform_window=timedelta(hours=24))


def test_new_contact_is_atomic_and_conversation_is_reused(
    db_session: Session,
) -> None:
    service = WhatsAppInboundService(db_session, provider())

    first = service.receive(inbound("wamid-new-1"), now=NOW)
    second = service.receive(
        inbound(
            "wamid-new-2",
            phone="+541144441234",
            occurred_at=NOW + timedelta(minutes=2),
        ),
        now=NOW + timedelta(minutes=2),
    )

    assert first.created is True
    assert first.customer_id is not None
    assert first.opportunity_id is not None
    assert first.suggested_opportunity_ids == ()
    assert second.conversation_id == first.conversation_id
    assert second.customer_id == first.customer_id
    assert second.opportunity_id is None
    assert (
        db_session.scalar(
            select(func.count(Customer.id)).where(Customer.id == first.customer_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count(Opportunity.id)).where(
                Opportunity.customer_id == first.customer_id
            )
        )
        == 1
    )

    customer = db_session.get(Customer, first.customer_id)
    opportunity = db_session.get(Opportunity, first.opportunity_id)
    conversation = db_session.get(WhatsAppConversation, first.conversation_id)
    assert customer is not None
    assert customer.name == "Cliente WA"
    assert opportunity is not None
    assert opportunity.source is LeadSource.WHATSAPP
    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.assigned_user_id is None
    assert conversation is not None
    assert conversation.unread_count == 2
    assert conversation.waiting_for_response is True
    assert conversation.waiting_since_at == NOW
    assert conversation.last_inbound_at == NOW + timedelta(minutes=2)
    assert conversation.window_expires_at == NOW + timedelta(hours=24, minutes=2)

    history = db_session.scalars(
        select(OpportunityStatusHistory).where(
            OpportunityStatusHistory.opportunity_id == opportunity.id
        )
    ).one()
    assert history.from_status is None
    assert history.to_status is OpportunityStatus.NUEVA
    link = db_session.scalars(
        select(WhatsAppConversationOpportunity).where(
            WhatsAppConversationOpportunity.conversation_id == conversation.id
        )
    ).one()
    assert link.opportunity_id == opportunity.id
    assert link.link_source is WhatsAppOpportunityLinkSource.AUTO_NEW_CONTACT
    assert link.unlinked_at is None


def test_inbound_replay_deduplicates_and_rejects_changed_payload(
    db_session: Session,
) -> None:
    service = WhatsAppInboundService(db_session, provider())
    original = inbound("wamid-idempotent")
    created = service.receive(original, now=NOW)

    replay = service.receive(original, now=NOW + timedelta(minutes=1))
    assert replay.created is False
    assert replay.message_id == created.message_id
    assert (
        db_session.scalar(
            select(func.count(WhatsAppMessage.id)).where(
                WhatsAppMessage.external_message_id == "wamid-idempotent"
            )
        )
        == 1
    )
    db_session.rollback()

    with pytest.raises(WhatsAppIdempotencyConflictError):
        service.receive(
            inbound("wamid-idempotent", body="Otro contenido"),
            now=NOW + timedelta(minutes=2),
        )


def test_existing_customer_is_matched_and_open_opportunity_only_suggested(
    db_session: Session,
) -> None:
    customer = Customer(name="Existente", phone="11 4444-9999")
    db_session.add(customer)
    db_session.flush()
    opportunity = OpportunityService(db_session).create_opportunity_in_transaction(
        customer_id=customer.id,
        source=LeadSource.WEB,
        assigned_user_id=None,
        changed_by_user_id=None,
    )
    db_session.commit()

    result = WhatsAppInboundService(db_session, provider()).receive(
        inbound("wamid-existing", phone="(11) 4444-9999"),
        now=NOW,
    )

    assert result.customer_id == customer.id
    assert result.opportunity_id is None
    assert result.suggested_opportunity_ids == (opportunity.id,)
    assert (
        db_session.scalar(
            select(func.count(Opportunity.id)).where(
                Opportunity.customer_id == customer.id
            )
        )
        == 1
    )
    assert (
        db_session.scalar(select(func.count(WhatsAppConversationOpportunity.id))) == 0
    )


@pytest.mark.parametrize("deleted", [False, True])
def test_ambiguous_or_deleted_phone_requires_review(
    db_session: Session,
    *,
    deleted: bool,
) -> None:
    customers = [
        Customer(
            name="Coincidencia uno",
            phone="+54 11 5555-8888",
            deleted_at=NOW if deleted else None,
        )
    ]
    if not deleted:
        customers.append(Customer(name="Coincidencia dos", phone="+541155558888"))
    db_session.add_all(customers)
    db_session.commit()

    result = WhatsAppInboundService(db_session, provider()).receive(
        inbound("wamid-review", phone="+54 (11) 5555 8888"),
        now=NOW,
    )

    conversation = db_session.get(WhatsAppConversation, result.conversation_id)
    assert result.customer_id is None
    assert result.opportunity_id is None
    assert conversation is not None
    assert conversation.resolution_status is WhatsAppConversationResolution.NEEDS_REVIEW
    assert conversation.customer_id is None
    assert (
        db_session.scalar(
            select(func.count(Opportunity.id)).where(
                Opportunity.customer_id.in_([customer.id for customer in customers])
            )
        )
        == 0
    )


def test_fallback_name_and_media_attachment_are_persisted(
    db_session: Session,
) -> None:
    result = WhatsAppInboundService(db_session, provider()).receive(
        inbound(
            "wamid-image",
            phone="11-2222-9876",
            display_name="   ",
            body="Foto de obra",
            message_type=WhatsAppMessageType.IMAGE,
            attachment=InboundAttachmentInput(
                provider_media_id="media-1",
                mime_type="image/jpeg",
                filename="obra.jpg",
                size_bytes=1234,
            ),
        ),
        now=NOW,
    )

    customer = db_session.get(Customer, result.customer_id)
    message = db_session.get(WhatsAppMessage, result.message_id)
    attachment = db_session.scalar(
        select(WhatsAppAttachment).where(
            WhatsAppAttachment.message_id == result.message_id
        )
    )
    assert customer is not None
    assert customer.name == "Contacto WhatsApp ••••9876"
    assert message is not None
    assert message.direction is WhatsAppDirection.INBOUND
    assert message.provider_state is WhatsAppProviderState.RECEIVED
    assert attachment is not None
    assert attachment.media_type is WhatsAppMessageType.IMAGE
    assert attachment.storage_status is WhatsAppStorageStatus.PENDING
    assert attachment.storage_key is None


def test_link_history_preserves_terminal_opportunities(
    db_session: Session,
    supervisor_user_id: int,
) -> None:
    customer = Customer(name="Cliente links", phone="1111111111")
    db_session.add(customer)
    db_session.flush()
    first = OpportunityService(db_session).create_opportunity_in_transaction(
        customer_id=customer.id,
        source=LeadSource.WEB,
        assigned_user_id=None,
        changed_by_user_id=None,
    )
    second = OpportunityService(db_session).create_opportunity_in_transaction(
        customer_id=customer.id,
        source=LeadSource.WEB,
        assigned_user_id=None,
        changed_by_user_id=None,
    )
    conversation = WhatsAppConversation(
        customer_id=customer.id,
        external_phone="1111111111",
        phone_match_key="1111111111",
        resolution_status=WhatsAppConversationResolution.RESOLVED,
    )
    db_session.add(conversation)
    db_session.commit()

    OpportunityService(db_session).mark_as_lost(
        first.id,
        LossReason.OTRO,
        changed_by_user_id=None,
    )
    assert first.status is OpportunityStatus.PERDIDA

    service = WhatsAppConversationService(db_session)
    first_link = service.link_opportunity(
        conversation.id,
        first.id,
        linked_by_user_id=supervisor_user_id,
        now=NOW,
    )
    second_link = service.link_opportunity(
        conversation.id,
        second.id,
        linked_by_user_id=supervisor_user_id,
        now=NOW + timedelta(minutes=1),
    )

    assert first_link.unlinked_at == NOW + timedelta(minutes=1)
    assert second_link.unlinked_at is None
    assert len(conversation.opportunity_links) == 2


def test_link_rejects_wrong_customer_and_unresolved_conversation(
    db_session: Session,
    supervisor_user_id: int,
) -> None:
    first_customer = Customer(name="Uno", phone="1000")
    second_customer = Customer(name="Dos", phone="2000")
    db_session.add_all([first_customer, second_customer])
    db_session.flush()
    opportunity = OpportunityService(db_session).create_opportunity_in_transaction(
        customer_id=second_customer.id,
        source=LeadSource.WEB,
        assigned_user_id=None,
        changed_by_user_id=None,
    )
    resolved = WhatsAppConversation(
        customer_id=first_customer.id,
        external_phone="1000",
        phone_match_key="1000",
        resolution_status=WhatsAppConversationResolution.RESOLVED,
    )
    unresolved = WhatsAppConversation(
        customer_id=None,
        external_phone="3000",
        phone_match_key="3000",
        resolution_status=WhatsAppConversationResolution.NEEDS_REVIEW,
    )
    db_session.add_all([resolved, unresolved])
    db_session.commit()
    resolved_id = resolved.id
    unresolved_id = unresolved.id
    opportunity_id = opportunity.id

    service = WhatsAppConversationService(db_session)
    with pytest.raises(WhatsAppOpportunityAssociationError):
        service.link_opportunity(
            resolved_id,
            opportunity_id,
            linked_by_user_id=supervisor_user_id,
            now=NOW,
        )
    db_session.rollback()
    with pytest.raises(WhatsAppConversationResolutionError):
        service.link_opportunity(
            unresolved_id,
            opportunity_id,
            linked_by_user_id=supervisor_user_id,
            now=NOW,
        )


def test_manual_customer_resolution_enables_opportunity_suggestions(
    db_session: Session,
) -> None:
    customer = Customer(name="Revisado", phone="+54 11 5555 8888")
    conversation = WhatsAppConversation(
        customer_id=None,
        external_phone="+54 11 5555 8888",
        phone_match_key="+541155558888",
        resolution_status=WhatsAppConversationResolution.NEEDS_REVIEW,
    )
    db_session.add_all([customer, conversation])
    db_session.commit()

    service = WhatsAppConversationService(db_session)
    resolved = service.resolve_customer(
        conversation.id,
        customer.id,
        now=NOW,
    )

    assert resolved.customer_id == customer.id
    assert resolved.resolution_status is WhatsAppConversationResolution.RESOLVED
    assert service.suggest_open_opportunities(conversation.id) == []


@pytest.fixture
def supervisor_user_id(supervisor_user: User) -> int:
    return supervisor_user.id


def test_new_contact_rolls_back_all_entities_if_opportunity_creation_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    phone = "+54 11 7000 4321"

    def fail_creation(
        service: OpportunityService,
        *,
        customer_id: int,
        source: LeadSource,
        assigned_user_id: int | None,
        changed_by_user_id: int | None,
    ) -> Opportunity:
        del service, customer_id, source, assigned_user_id, changed_by_user_id
        raise RuntimeError("Injected opportunity failure")

    monkeypatch.setattr(
        OpportunityService,
        "create_opportunity_in_transaction",
        fail_creation,
    )

    with pytest.raises(RuntimeError, match="Injected opportunity failure"):
        WhatsAppInboundService(db_session, provider()).receive(
            inbound("wamid-rollback", phone=phone),
            now=NOW,
        )

    assert db_session.scalar(select(Customer).where(Customer.phone == phone)) is None
    assert (
        db_session.scalar(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_match_key == "+541170004321"
            )
        )
        is None
    )
    assert (
        db_session.scalar(
            select(WhatsAppMessage).where(
                WhatsAppMessage.external_message_id == "wamid-rollback"
            )
        )
        is None
    )


def test_concurrent_duplicate_inbound_creates_one_message_and_conversation() -> None:
    external_id = "wamid-concurrent-phase2"
    phone = "+54 11 7999 0001"
    fake = provider()

    def receive_once() -> tuple[int, int, bool]:
        with SessionLocal() as session:
            result = WhatsAppInboundService(session, fake).receive(
                inbound(external_id, phone=phone),
                now=NOW,
            )
            return result.conversation_id, result.message_id, result.created

    def receive_index(index: int) -> tuple[int, int, bool]:
        del index
        return receive_once()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(receive_index, range(2)))

        assert results[0][0:2] == results[1][0:2]
        assert sorted(result[2] for result in results) == [False, True]
        with SessionLocal() as verification:
            assert (
                verification.scalar(
                    select(func.count(WhatsAppMessage.id)).where(
                        WhatsAppMessage.external_message_id == external_id
                    )
                )
                == 1
            )
    finally:
        with SessionLocal.begin() as cleanup:
            conversation = cleanup.scalar(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.phone_match_key == "+541179990001"
                )
            )
            if conversation is not None:
                message_ids = select(WhatsAppMessage.id).where(
                    WhatsAppMessage.conversation_id == conversation.id
                )
                opportunity_ids = tuple(
                    cleanup.scalars(
                        select(WhatsAppConversationOpportunity.opportunity_id).where(
                            WhatsAppConversationOpportunity.conversation_id
                            == conversation.id
                        )
                    )
                )
                customer_id = conversation.customer_id
                cleanup.execute(
                    delete(WhatsAppAttachment).where(
                        WhatsAppAttachment.message_id.in_(message_ids)
                    )
                )
                cleanup.execute(
                    delete(WhatsAppConversationOpportunity).where(
                        WhatsAppConversationOpportunity.conversation_id
                        == conversation.id
                    )
                )
                cleanup.execute(
                    delete(WhatsAppMessage).where(
                        WhatsAppMessage.conversation_id == conversation.id
                    )
                )
                cleanup.execute(
                    delete(WhatsAppConversation).where(
                        WhatsAppConversation.id == conversation.id
                    )
                )
                cleanup.execute(
                    delete(OpportunityStatusHistory).where(
                        OpportunityStatusHistory.opportunity_id.in_(opportunity_ids)
                    )
                )
                cleanup.execute(
                    delete(Opportunity).where(Opportunity.id.in_(opportunity_ids))
                )
                if customer_id is not None:
                    cleanup.execute(delete(Customer).where(Customer.id == customer_id))
