from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Notification,
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
from app.services.errors import (
    ActiveOpportunityExistsError,
    WhatsAppConversationResolutionError,
)
from app.whatsapp import FakeWhatsAppProvider
from app.whatsapp.webhook_contracts import ProviderInboundReferral

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
    assert second.opportunity_id == first.opportunity_id
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
    assert opportunity.initial_whatsapp_message_id == first.message_id
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


@pytest.mark.parametrize(
    "existing_source",
    [LeadSource.WEB, LeadSource.INSTAGRAM, LeadSource.REFERIDO],
)
def test_existing_customer_with_active_non_whatsapp_gets_new_whatsapp_opportunity(
    db_session: Session,
    existing_source: LeadSource,
) -> None:
    customer = Customer(name="Existente", phone="11 4444-9999")
    db_session.add(customer)
    db_session.flush()
    existing_opportunity = OpportunityService(
        db_session
    ).create_opportunity_in_transaction(
        customer_id=customer.id,
        source=existing_source,
        assigned_user_id=None,
        changed_by_user_id=None,
    )
    db_session.commit()

    result = WhatsAppInboundService(db_session, provider()).receive(
        inbound("wamid-existing", phone="(11) 4444-9999"),
        now=NOW,
    )

    assert result.customer_id == customer.id
    assert result.opportunity_id != existing_opportunity.id
    assert result.suggested_opportunity_ids == ()
    assert (
        db_session.scalar(
            select(func.count(Opportunity.id)).where(
                Opportunity.customer_id == customer.id
            )
        )
        == 2
    )
    assert (
        db_session.scalar(select(func.count(WhatsAppConversationOpportunity.id))) == 1
    )
    whatsapp_opportunity = db_session.get(Opportunity, result.opportunity_id)
    assert whatsapp_opportunity is not None
    assert whatsapp_opportunity.source is LeadSource.WHATSAPP
    assert whatsapp_opportunity.initial_whatsapp_message_id == result.message_id


def test_existing_customer_with_active_whatsapp_reuses_it(
    db_session: Session,
) -> None:
    customer = Customer(name="Existente WhatsApp", phone="+54 15 456-7818")
    db_session.add(customer)
    db_session.flush()
    opportunity = OpportunityService(db_session).create_opportunity_in_transaction(
        customer_id=customer.id,
        source=LeadSource.WHATSAPP,
        assigned_user_id=None,
        changed_by_user_id=None,
    )
    db_session.commit()

    result = WhatsAppInboundService(db_session, provider()).receive(
        inbound("wamid-existing-whatsapp", phone="5492494567818"),
        now=NOW,
    )

    assert result.customer_id == customer.id
    assert customer.phone == "+54 15 456-7818"
    assert result.opportunity_id == opportunity.id
    assert (
        db_session.scalar(
            select(func.count(Opportunity.id)).where(
                Opportunity.customer_id == customer.id
            )
        )
        == 1
    )
    db_session.refresh(opportunity)
    assert opportunity.initial_whatsapp_message_id is None


def test_existing_customer_without_active_opportunity_gets_new_whatsapp_opportunity(
    db_session: Session,
) -> None:
    customer = Customer(name="Cliente histórico", phone="11 4333 2222")
    db_session.add(customer)
    db_session.commit()

    result = WhatsAppInboundService(db_session, provider()).receive(
        inbound("wamid-existing-closed", phone="1143332222"),
        now=NOW,
    )

    opportunity = db_session.get(Opportunity, result.opportunity_id)
    assert opportunity is not None
    assert opportunity.customer_id == customer.id
    assert opportunity.source is LeadSource.WHATSAPP
    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.initial_whatsapp_message_id == result.message_id


@pytest.mark.parametrize(
    "closed_status",
    [OpportunityStatus.GANADA, OpportunityStatus.PERDIDA],
)
def test_inbound_after_closed_opportunity_creates_new_history(
    db_session: Session,
    closed_status: OpportunityStatus,
) -> None:
    service = WhatsAppInboundService(db_session, provider())
    first = service.receive(inbound(f"wamid-before-{closed_status.value}"), now=NOW)
    original = db_session.get(Opportunity, first.opportunity_id)
    assert original is not None
    original.status = closed_status
    original.loss_reason = (
        LossReason.OTRO if closed_status is OpportunityStatus.PERDIDA else None
    )
    original.loss_reason_detail = (
        "Cierre de prueba" if closed_status is OpportunityStatus.PERDIDA else None
    )
    db_session.commit()

    second = service.receive(
        inbound(
            f"wamid-after-{closed_status.value}",
            occurred_at=NOW + timedelta(days=1),
        ),
        now=NOW + timedelta(days=1),
    )

    created = db_session.get(Opportunity, second.opportunity_id)
    db_session.refresh(original)
    assert created is not None
    assert created.id != original.id
    assert created.status is OpportunityStatus.NUEVA
    assert created.initial_whatsapp_message_id == second.message_id
    assert original.status is closed_status


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
        "Motivo de prueba",
        changed_by_user_id=None,
        note="Seguimiento de prueba CRM-057",
    )
    assert first.status is OpportunityStatus.PERDIDA

    second = OpportunityService(db_session).create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        assigned_user_id=None,
        changed_by_user_id=None,
    )

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
            cleanup.execute(text("SET LOCAL asfaltos.test_cleanup = 'on'"))
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
                    delete(Notification).where(
                        Notification.opportunity_id.in_(opportunity_ids)
                    )
                )
                cleanup.execute(
                    delete(Opportunity).where(Opportunity.id.in_(opportunity_ids))
                )
                if customer_id is not None:
                    cleanup.execute(delete(Customer).where(Customer.id == customer_id))


def test_concurrent_distinct_inbound_creates_at_most_one_active_opportunity() -> None:
    phone = "+54 11 7999 0002"
    fake = provider()
    with SessionLocal.begin() as setup:
        setup.add(Customer(name="Cliente concurrente", phone=phone))

    def receive_once(index: int) -> tuple[int, int]:
        with SessionLocal() as session:
            result = WhatsAppInboundService(session, fake).receive(
                replace(
                    inbound(f"wamid-concurrent-active-{index}", phone=phone),
                    referral=ProviderInboundReferral(source_type="ad")
                    if index
                    else None,
                ),
                now=NOW + timedelta(seconds=index),
            )
            assert result.opportunity_id is not None
            return result.message_id, result.opportunity_id

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(receive_once, range(2)))

        assert results[0][1] == results[1][1]
        with SessionLocal() as verification:
            customer_id = verification.scalar(
                select(Customer.id).where(Customer.phone == phone)
            )
            assert customer_id is not None
            assert (
                verification.scalar(
                    select(func.count(Opportunity.id)).where(
                        Opportunity.customer_id == customer_id,
                        Opportunity.status.in_(
                            {
                                OpportunityStatus.NUEVA,
                                OpportunityStatus.COTIZADA,
                                OpportunityStatus.NEGOCIACION,
                            }
                        ),
                        Opportunity.deleted_at.is_(None),
                    )
                )
                == 1
            )
            assert (
                verification.scalar(
                    select(func.count(WhatsAppMessage.id)).where(
                        WhatsAppMessage.external_message_id.in_(
                            {"wamid-concurrent-active-0", "wamid-concurrent-active-1"}
                        )
                    )
                )
                == 2
            )
    finally:
        with SessionLocal.begin() as cleanup:
            cleanup.execute(text("SET LOCAL asfaltos.test_cleanup = 'on'"))
            customer_id = cleanup.scalar(
                select(Customer.id).where(Customer.phone == phone)
            )
            if customer_id is not None:
                conversation_ids = select(WhatsAppConversation.id).where(
                    WhatsAppConversation.customer_id == customer_id
                )
                message_ids = select(WhatsAppMessage.id).where(
                    WhatsAppMessage.conversation_id.in_(conversation_ids)
                )
                opportunity_ids = select(Opportunity.id).where(
                    Opportunity.customer_id == customer_id
                )
                cleanup.execute(
                    delete(WhatsAppAttachment).where(
                        WhatsAppAttachment.message_id.in_(message_ids)
                    )
                )
                cleanup.execute(
                    delete(WhatsAppConversationOpportunity).where(
                        WhatsAppConversationOpportunity.conversation_id.in_(
                            conversation_ids
                        )
                    )
                )
                cleanup.execute(
                    delete(WhatsAppMessage).where(
                        WhatsAppMessage.conversation_id.in_(conversation_ids)
                    )
                )
                cleanup.execute(
                    delete(WhatsAppConversation).where(
                        WhatsAppConversation.id.in_(conversation_ids)
                    )
                )
                cleanup.execute(
                    delete(OpportunityStatusHistory).where(
                        OpportunityStatusHistory.opportunity_id.in_(opportunity_ids)
                    )
                )
                cleanup.execute(
                    delete(Notification).where(
                        Notification.opportunity_id.in_(opportunity_ids)
                    )
                )
                cleanup.execute(
                    delete(Opportunity).where(Opportunity.id.in_(opportunity_ids))
                )
                cleanup.execute(delete(Customer).where(Customer.id == customer_id))


@pytest.mark.parametrize("ad_first", [False, True])
def test_initial_referral_classifies_case_and_later_messages_preserve_it(
    db_session: Session,
    *,
    ad_first: bool,
) -> None:
    service = WhatsAppInboundService(db_session, provider())
    referral = ProviderInboundReferral(
        source_type="ad",
        source_id="ad-123",
        source_url="https://fb.me/example",
        ctwa_clid="click-123",
    )
    first_input = replace(
        inbound(
            "wamid-meta-initial", body="Hola Cuál es el precio de la bolsa de BituBach?"
        ),
        referral=referral if ad_first else None,
    )
    first = service.receive(first_input, now=NOW)
    replay = service.receive(first_input, now=NOW)
    assert replay.created is False
    second = service.receive(
        replace(inbound("wamid-meta-second"), referral=None if ad_first else referral),
        now=NOW,
    )
    assert second.opportunity_id == first.opportunity_id
    opportunity = db_session.get(Opportunity, first.opportunity_id)
    message = db_session.get(WhatsAppMessage, first.message_id)
    assert opportunity is not None and message is not None
    assert opportunity.source is (LeadSource.META if ad_first else LeadSource.WHATSAPP)
    assert opportunity.initial_whatsapp_message_id == first.message_id
    assert message.referral_source_id == ("ad-123" if ad_first else None)
    assert message.referral_ctwa_clid == ("click-123" if ad_first else None)
    db_session.commit()
    with pytest.raises(WhatsAppIdempotencyConflictError):
        service.receive(
            replace(
                first_input,
                referral=ProviderInboundReferral(
                    source_type="ad", source_id="different-ad"
                ),
            ),
            now=NOW,
        )


@pytest.mark.parametrize("source_type", [None, "ad", "post", ""])
def test_referral_type_controls_attribution_without_requiring_click_id(
    db_session: Session,
    source_type: str | None,
) -> None:
    result = WhatsAppInboundService(db_session, provider()).receive(
        replace(
            inbound("wamid-referral-type"),
            referral=ProviderInboundReferral(source_type=source_type),
        ),
        now=NOW,
    )
    opportunity = db_session.get(Opportunity, result.opportunity_id)
    assert opportunity is not None
    assert opportunity.source is (
        LeadSource.META if source_type == "ad" else LeadSource.WHATSAPP
    )


def test_closed_meta_case_starts_next_case_with_new_initial_source(
    db_session: Session,
) -> None:
    service = WhatsAppInboundService(db_session, provider())
    first = service.receive(
        replace(
            inbound("wamid-meta-closed"),
            referral=ProviderInboundReferral(source_type="ad"),
        ),
        now=NOW,
    )
    original = db_session.get(Opportunity, first.opportunity_id)
    assert original is not None
    original.status = OpportunityStatus.GANADA
    db_session.commit()
    second = service.receive(inbound("wamid-organic-next"), now=NOW)
    created = db_session.get(Opportunity, second.opportunity_id)
    assert created is not None and created.id != first.opportunity_id
    assert created.source is LeadSource.WHATSAPP
    db_session.refresh(original)
    assert original.source is LeadSource.META


@pytest.mark.parametrize(
    "first_source, second_source",
    [(LeadSource.META, LeadSource.WHATSAPP), (LeadSource.WHATSAPP, LeadSource.META)],
)
def test_ad_and_organic_cases_share_the_channel_creation_limit(
    db_session: Session,
    first_source: LeadSource,
    second_source: LeadSource,
) -> None:
    customer = Customer(name="Canal WhatsApp compartido")
    db_session.add(customer)
    db_session.commit()
    customer_id = customer.id
    service = OpportunityService(db_session)
    service.create_opportunity(customer_id=customer_id, source=first_source)

    with pytest.raises(ActiveOpportunityExistsError):
        service.create_opportunity(customer_id=customer_id, source=second_source)


@pytest.mark.parametrize("manual_creation", [False, True])
def test_identity_review_preserves_the_pending_first_ad_inquiry(
    db_session: Session,
    supervisor_user_id: int,
    *,
    manual_creation: bool,
) -> None:
    phone = "+541177770061"
    customer = Customer(name="Cliente a revisar", phone=phone)
    db_session.add_all([customer, Customer(name="Coincidencia duplicada", phone=phone)])
    db_session.commit()
    customer_id = customer.id
    intake = WhatsAppInboundService(db_session, provider())
    first = intake.receive(
        replace(
            inbound("wamid-review-ad", phone=phone),
            referral=ProviderInboundReferral(source_type="ad"),
        ),
        now=NOW,
    )
    assert first.customer_id is None and first.opportunity_id is None
    conversations = WhatsAppConversationService(db_session)
    conversations.resolve_customer(first.conversation_id, customer_id, now=NOW)
    opportunity: Opportunity | None
    if manual_creation:
        opportunity = conversations.create_opportunity(
            first.conversation_id, changed_by_user_id=supervisor_user_id
        )
    else:
        second = intake.receive(inbound("wamid-review-followup", phone=phone), now=NOW)
        opportunity = db_session.get(Opportunity, second.opportunity_id)
    assert opportunity is not None
    assert opportunity.source is LeadSource.META
    assert opportunity.initial_whatsapp_message_id == first.message_id


def test_legacy_message_retry_can_complete_referral_evidence_without_reclassifying_case(
    db_session: Session,
) -> None:
    intake = WhatsAppInboundService(db_session, provider())
    original_input = inbound("wamid-legacy-referral")
    original = intake.receive(original_input, now=NOW)
    message = db_session.get(WhatsAppMessage, original.message_id)
    assert message is not None
    message.referral_captured = False
    db_session.commit()
    retry = intake.receive(
        replace(
            original_input,
            referral=ProviderInboundReferral(source_type="ad", source_id="old-ad"),
        ),
        now=NOW,
    )
    assert retry.created is False
    assert retry.message_id == original.message_id
    assert retry.opportunity_id == original.opportunity_id
    db_session.refresh(message)
    assert message.referral_captured is True
    assert message.referral_source_id == "old-ad"
    opportunity = db_session.get(Opportunity, original.opportunity_id)
    assert opportunity is not None
    assert opportunity.source is LeadSource.WHATSAPP
