from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Opportunity,
    OpportunityStatus,
    User,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
    WhatsAppOpportunityLinkSource,
)
from app.services.errors import (
    EntityNotFoundError,
    WhatsAppConversationResolutionError,
    WhatsAppOpportunityAssociationError,
)
from app.services.whatsapp_projection_service import later_datetime

OPEN_OPPORTUNITY_STATUSES = frozenset(
    {
        OpportunityStatus.NUEVA,
        OpportunityStatus.COTIZADA,
        OpportunityStatus.NEGOCIACION,
    }
)


class WhatsAppConversationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def mark_as_read(
        self,
        conversation_id: int,
        *,
        now: datetime | None = None,
    ) -> WhatsAppConversation:
        read_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            conversation = self._get_for_update(conversation_id)
            conversation.unread_count = 0
            conversation.updated_at = later_datetime(
                conversation.updated_at,
                read_at,
            )
            self._session.flush()
        return conversation

    def resolve_customer(
        self,
        conversation_id: int,
        customer_id: int,
        *,
        now: datetime | None = None,
    ) -> WhatsAppConversation:
        resolved_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            conversation = self._get_for_update(conversation_id)
            customer = self._session.scalar(
                select(Customer)
                .where(
                    Customer.id == customer_id,
                    Customer.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if customer is None:
                raise EntityNotFoundError("Customer", customer_id)
            conversation.customer_id = customer.id
            conversation.resolution_status = WhatsAppConversationResolution.RESOLVED
            conversation.updated_at = later_datetime(
                conversation.updated_at,
                resolved_at,
            )
            self._session.flush()
        return conversation

    def link_opportunity(
        self,
        conversation_id: int,
        opportunity_id: int,
        *,
        linked_by_user_id: int,
        now: datetime | None = None,
    ) -> WhatsAppConversationOpportunity:
        linked_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            conversation = self._get_for_update(conversation_id)
            return self.link_opportunity_in_transaction(
                conversation=conversation,
                opportunity_id=opportunity_id,
                link_source=WhatsAppOpportunityLinkSource.MANUAL,
                linked_by_user_id=linked_by_user_id,
                linked_at=linked_at,
            )

    def link_opportunity_in_transaction(
        self,
        *,
        conversation: WhatsAppConversation,
        opportunity_id: int,
        link_source: WhatsAppOpportunityLinkSource,
        linked_by_user_id: int | None,
        linked_at: datetime,
    ) -> WhatsAppConversationOpportunity:
        if (
            conversation.resolution_status
            is not WhatsAppConversationResolution.RESOLVED
            or conversation.customer_id is None
        ):
            raise WhatsAppConversationResolutionError(
                "Conversation must be resolved before linking an opportunity"
            )
        customer = self._session.get(Customer, conversation.customer_id)
        if customer is None or customer.deleted_at is not None:
            raise WhatsAppConversationResolutionError(
                "Conversation customer is not available"
            )
        opportunity = self._session.scalar(
            select(Opportunity)
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if opportunity is None:
            raise EntityNotFoundError("Opportunity", opportunity_id)
        if opportunity.customer_id != conversation.customer_id:
            raise WhatsAppOpportunityAssociationError(
                "Conversation and opportunity must belong to the same customer"
            )
        if linked_by_user_id is not None:
            user = self._session.get(User, linked_by_user_id)
            if user is None:
                raise EntityNotFoundError("User", linked_by_user_id)

        current = self._active_link_for_update(conversation.id)
        if current is not None and current.opportunity_id == opportunity_id:
            return current
        if current is not None:
            current.unlinked_at = linked_at

        link = WhatsAppConversationOpportunity(
            conversation_id=conversation.id,
            opportunity_id=opportunity_id,
            linked_at=linked_at,
            linked_by_user_id=linked_by_user_id,
            link_source=link_source,
        )
        self._session.add(link)
        conversation.updated_at = later_datetime(
            conversation.updated_at,
            linked_at,
        )
        self._session.flush()
        return link

    def suggest_open_opportunities(
        self,
        conversation_id: int,
    ) -> list[Opportunity]:
        conversation = self._session.get(WhatsAppConversation, conversation_id)
        if conversation is None:
            raise EntityNotFoundError("WhatsAppConversation", conversation_id)
        if conversation.customer_id is None:
            return []
        return list(
            self._session.scalars(
                select(Opportunity)
                .where(
                    Opportunity.customer_id == conversation.customer_id,
                    Opportunity.status.in_(OPEN_OPPORTUNITY_STATUSES),
                    Opportunity.deleted_at.is_(None),
                )
                .order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
            )
        )

    def _get_for_update(self, conversation_id: int) -> WhatsAppConversation:
        conversation = self._session.scalar(
            select(WhatsAppConversation)
            .where(WhatsAppConversation.id == conversation_id)
            .with_for_update()
        )
        if conversation is None:
            raise EntityNotFoundError("WhatsAppConversation", conversation_id)
        return conversation

    def _active_link_for_update(
        self,
        conversation_id: int,
    ) -> WhatsAppConversationOpportunity | None:
        return self._session.scalar(
            select(WhatsAppConversationOpportunity)
            .where(
                WhatsAppConversationOpportunity.conversation_id == conversation_id,
                WhatsAppConversationOpportunity.unlinked_at.is_(None),
            )
            .with_for_update()
        )

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
