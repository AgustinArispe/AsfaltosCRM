from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityStatus,
    User,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
    WhatsAppOpportunityLinkSource,
)
from app.services.customer_identity_service import comparable_phone
from app.services.errors import (
    EntityNotFoundError,
    InvalidWhatsAppMessageError,
    WhatsAppConversationResolutionError,
    WhatsAppOpportunityAssociationError,
)
from app.services.opportunity_service import OpportunityService
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

    def hide_conversation(
        self,
        conversation_id: int,
        *,
        now: datetime | None = None,
    ) -> None:
        hidden_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            conversation = self._get_for_update(conversation_id, include_hidden=True)
            if conversation.deleted_at is None:
                conversation.deleted_at = hidden_at
                conversation.updated_at = later_datetime(
                    conversation.updated_at, hidden_at
                )
                self._session.flush()

    def open_or_create_for_opportunity(
        self,
        opportunity_id: int,
        *,
        changed_by_user_id: int,
        now: datetime | None = None,
    ) -> WhatsAppConversation:
        opened_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
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
            customer = self._session.scalar(
                select(Customer)
                .where(
                    Customer.id == opportunity.customer_id,
                    Customer.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if customer is None:
                raise EntityNotFoundError("Customer", opportunity.customer_id)
            phone_match_key = comparable_phone(customer.phone)
            if phone_match_key is None:
                raise InvalidWhatsAppMessageError(
                    "Opportunity customer must have a valid phone number"
                )
            conversation = self._session.scalar(
                select(WhatsAppConversation)
                .where(WhatsAppConversation.phone_match_key == phone_match_key)
                .with_for_update()
            )
            if conversation is None:
                conversation = WhatsAppConversation(
                    customer_id=customer.id,
                    external_phone=phone_match_key,
                    phone_match_key=phone_match_key,
                    resolution_status=WhatsAppConversationResolution.RESOLVED,
                    updated_at=opened_at,
                )
                self._session.add(conversation)
                self._session.flush()
            elif conversation.customer_id not in {None, customer.id}:
                raise WhatsAppOpportunityAssociationError(
                    "WhatsApp conversation belongs to a different customer"
                )
            else:
                conversation.customer_id = customer.id
                conversation.resolution_status = WhatsAppConversationResolution.RESOLVED
                conversation.deleted_at = None
                conversation.updated_at = later_datetime(
                    conversation.updated_at, opened_at
                )
            self.link_opportunity_in_transaction(
                conversation=conversation,
                opportunity_id=opportunity.id,
                link_source=WhatsAppOpportunityLinkSource.MANUAL,
                linked_by_user_id=changed_by_user_id,
                linked_at=opened_at,
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

    def create_opportunity(
        self,
        conversation_id: int,
        *,
        changed_by_user_id: int,
    ) -> Opportunity:
        """Create a server-owned WhatsApp opportunity for a resolved conversation."""
        customer_id = self._conversation_customer_id(conversation_id)
        self._session.rollback()
        with self._session.begin():
            customer = self._session.scalar(
                select(Customer)
                .where(Customer.id == customer_id, Customer.deleted_at.is_(None))
                .with_for_update()
            )
            if customer is None:
                raise WhatsAppConversationResolutionError(
                    "Conversation customer is not available"
                )
            conversation = self._get_for_update(conversation_id)
            if (
                conversation.resolution_status
                is not WhatsAppConversationResolution.RESOLVED
                or conversation.customer_id != customer.id
            ):
                raise WhatsAppConversationResolutionError(
                    "Conversation must be resolved before creating an opportunity"
                )
            return OpportunityService(self._session).create_opportunity_in_transaction(
                customer_id=customer.id,
                source=LeadSource.WHATSAPP,
                changed_by_user_id=changed_by_user_id,
            )

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

    def unlink_opportunity(
        self,
        conversation_id: int,
        *,
        now: datetime | None = None,
    ) -> WhatsAppConversationOpportunity | None:
        unlinked_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            conversation = self._get_for_update(conversation_id)
            current = self._active_link_for_update(conversation.id)
            if current is None:
                return None
            current.unlinked_at = unlinked_at
            conversation.updated_at = later_datetime(
                conversation.updated_at,
                unlinked_at,
            )
            self._session.flush()
            return current

    def suggest_open_opportunities(
        self,
        conversation_id: int,
    ) -> list[Opportunity]:
        conversation = self._session.scalar(
            select(WhatsAppConversation).where(
                WhatsAppConversation.id == conversation_id,
                WhatsAppConversation.deleted_at.is_(None),
            )
        )
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

    def _get_for_update(
        self,
        conversation_id: int,
        *,
        include_hidden: bool = False,
    ) -> WhatsAppConversation:
        filters = [WhatsAppConversation.id == conversation_id]
        if not include_hidden:
            filters.append(WhatsAppConversation.deleted_at.is_(None))
        conversation = self._session.scalar(
            select(WhatsAppConversation).where(*filters).with_for_update()
        )
        if conversation is None:
            raise EntityNotFoundError("WhatsAppConversation", conversation_id)
        return conversation

    def _conversation_customer_id(self, conversation_id: int) -> int:
        conversation = self._session.scalar(
            select(WhatsAppConversation).where(
                WhatsAppConversation.id == conversation_id,
                WhatsAppConversation.deleted_at.is_(None),
            )
        )
        if conversation is None:
            raise EntityNotFoundError("WhatsAppConversation", conversation_id)
        if (
            conversation.resolution_status
            is not WhatsAppConversationResolution.RESOLVED
            or conversation.customer_id is None
        ):
            raise WhatsAppConversationResolutionError(
                "Conversation must be resolved before creating an opportunity"
            )
        return conversation.customer_id

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
