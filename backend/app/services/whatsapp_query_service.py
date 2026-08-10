from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import PurePath
from time import perf_counter

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, joinedload, load_only, raiseload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.sql.elements import Case, ColumnElement, UnaryExpression

from app.models import (
    Customer,
    Opportunity,
    OpportunityStatus,
    User,
    WhatsAppAttachment,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppMessage,
    WhatsAppMessageStatusEvent,
    WhatsAppStorageStatus,
)
from app.services.customer_identity_service import comparable_phone
from app.services.errors import EntityNotFoundError
from app.services.whatsapp_query_observability import (
    NullWhatsAppQueryMetrics,
    QueryErrorMeasurement,
    QueryMeasurement,
    WhatsAppProjectionType,
    WhatsAppQueryErrorCategory,
    WhatsAppQueryMetrics,
    WhatsAppQueryOperation,
    WhatsAppQueryOutcome,
)
from app.services.whatsapp_query_projections import (
    AttachmentContentReference,
    AttachmentProjection,
    ChangePageRequest,
    ConversationChangePage,
    ConversationDetailProjection,
    ConversationListFilters,
    ConversationPage,
    ConversationPageCursor,
    ConversationPageRequest,
    ConversationSummaryProjection,
    CustomerSummaryProjection,
    MessageChangePage,
    MessagePage,
    MessagePageCursor,
    MessagePageRequest,
    MessageProjection,
    MessageStatusProjection,
    OpportunityLinkProjection,
    OpportunitySummaryProjection,
    ResourceChangeCursor,
    UserSummaryProjection,
)

_MAX_BIGINT = 9_223_372_036_854_775_807
_OPEN_OPPORTUNITY_STATUSES = (
    OpportunityStatus.NUEVA,
    OpportunityStatus.COTIZADA,
    OpportunityStatus.NEGOCIACION,
)


class ConversationQueryService:
    def __init__(
        self,
        session: Session,
        metrics: WhatsAppQueryMetrics | None = None,
    ) -> None:
        self._session = session
        self._metrics = metrics or NullWhatsAppQueryMetrics()

    def list_conversations(
        self,
        filters: ConversationListFilters,
        page: ConversationPageRequest,
        *,
        snapshot_at: datetime | None = None,
    ) -> ConversationPage:
        started_at = perf_counter()
        statements = 0
        snapshot = self._snapshot(page.cursor, snapshot_at)
        change_key = _conversation_change_key()
        query_filters: list[ColumnElement[bool]] = [change_key <= snapshot]
        if filters.waiting_only:
            query_filters.append(WhatsAppConversation.waiting_for_response.is_(True))
        if filters.unread_only:
            query_filters.append(WhatsAppConversation.unread_count > 0)
        search_filter = _conversation_search_filter(filters.search)
        if search_filter is not None:
            query_filters.append(search_filter)
        if page.cursor is not None:
            query_filters.append(_conversation_after_cursor(page.cursor))

        statement = (
            select(WhatsAppConversation, change_key.label("resource_updated_at"))
            .outerjoin(Customer, Customer.id == WhatsAppConversation.customer_id)
            .where(*query_filters)
            .options(
                raiseload("*"),
                load_only(
                    WhatsAppConversation.id,
                    WhatsAppConversation.customer_id,
                    WhatsAppConversation.external_phone,
                    WhatsAppConversation.display_name,
                    WhatsAppConversation.resolution_status,
                    WhatsAppConversation.last_message_at,
                    WhatsAppConversation.last_inbound_at,
                    WhatsAppConversation.last_outbound_at,
                    WhatsAppConversation.unread_count,
                    WhatsAppConversation.waiting_for_response,
                    WhatsAppConversation.waiting_since_at,
                    WhatsAppConversation.window_expires_at,
                    WhatsAppConversation.created_at,
                    WhatsAppConversation.updated_at,
                    raiseload=True,
                ),
                joinedload(WhatsAppConversation.customer).load_only(
                    Customer.id,
                    Customer.name,
                    Customer.company,
                    Customer.phone,
                    Customer.province,
                    Customer.deleted_at,
                    raiseload=True,
                ),
            )
            .order_by(*_conversation_order())
            .limit(page.limit + 1)
        )
        try:
            with self._session.no_autoflush:
                rows = list(self._session.execute(statement).tuples())
                statements += 1
                has_more = len(rows) > page.limit
                selected_rows = rows[: page.limit]
                conversations = [row[0] for row in selected_rows]
                active_links, suggestions, relation_statements = (
                    self._load_summary_relations(conversations)
                )
                statements += relation_statements
                items = tuple(
                    self._summary_projection(
                        conversation,
                        resource_updated_at,
                        active_links.get(conversation.id),
                        suggestions.get(conversation.customer_id, ()),
                    )
                    for conversation, resource_updated_at in selected_rows
                )
            next_cursor = (
                _conversation_cursor(items[-1], snapshot)
                if has_more and items
                else None
            )
            result = ConversationPage(
                items=items,
                next_cursor=next_cursor,
                sync_cursor=ResourceChangeCursor(snapshot, _MAX_BIGINT),
            )
        except Exception:
            self._record_failure(
                WhatsAppQueryOperation.CONVERSATION_LIST,
                started_at,
                statements,
                WhatsAppQueryErrorCategory.INTERNAL,
            )
            raise
        self._record_success(
            WhatsAppQueryOperation.CONVERSATION_LIST,
            started_at,
            len(result.items),
            statements,
        )
        return result

    def get_conversation_detail(
        self,
        conversation_id: int,
    ) -> ConversationDetailProjection:
        started_at = perf_counter()
        statements = 0
        change_key = _conversation_change_key()
        statement = (
            select(WhatsAppConversation, change_key.label("resource_updated_at"))
            .outerjoin(Customer, Customer.id == WhatsAppConversation.customer_id)
            .where(WhatsAppConversation.id == conversation_id)
            .options(
                raiseload("*"),
                load_only(
                    WhatsAppConversation.id,
                    WhatsAppConversation.customer_id,
                    WhatsAppConversation.external_phone,
                    WhatsAppConversation.display_name,
                    WhatsAppConversation.resolution_status,
                    WhatsAppConversation.last_message_at,
                    WhatsAppConversation.last_inbound_at,
                    WhatsAppConversation.last_outbound_at,
                    WhatsAppConversation.unread_count,
                    WhatsAppConversation.waiting_for_response,
                    WhatsAppConversation.waiting_since_at,
                    WhatsAppConversation.window_expires_at,
                    WhatsAppConversation.created_at,
                    WhatsAppConversation.updated_at,
                    raiseload=True,
                ),
                joinedload(WhatsAppConversation.customer).load_only(
                    Customer.id,
                    Customer.name,
                    Customer.company,
                    Customer.phone,
                    Customer.province,
                    Customer.deleted_at,
                    raiseload=True,
                ),
            )
        )
        try:
            with self._session.no_autoflush:
                row = self._session.execute(statement).tuples().one_or_none()
                statements += 1
                conversation, resource_updated_at = _require_entity(
                    row,
                    "WhatsAppConversation",
                    conversation_id,
                )
                links = self._load_links((conversation.id,))
                statements += 1
                suggestions = self._load_suggestions(
                    (conversation.customer_id,)
                    if conversation.customer_id is not None
                    and conversation.customer is not None
                    and conversation.customer.deleted_at is None
                    else ()
                )
                statements += (
                    1
                    if conversation.customer_id is not None
                    and conversation.customer is not None
                    and conversation.customer.deleted_at is None
                    else 0
                )
                active_link = next(
                    (link for link in links if link.unlinked_at is None),
                    None,
                )
                summary = self._summary_projection(
                    conversation,
                    resource_updated_at,
                    active_link,
                    suggestions.get(conversation.customer_id, ()),
                )
                history = tuple(
                    self._link_projection(link, conversation.customer) for link in links
                )
                result = ConversationDetailProjection(
                    summary=summary,
                    opportunity_links=history,
                    created_at=conversation.created_at,
                )
        except EntityNotFoundError:
            self._record_failure(
                WhatsAppQueryOperation.CONVERSATION_DETAIL,
                started_at,
                statements,
                WhatsAppQueryErrorCategory.NOT_FOUND,
            )
            raise
        except Exception:
            self._record_failure(
                WhatsAppQueryOperation.CONVERSATION_DETAIL,
                started_at,
                statements,
                WhatsAppQueryErrorCategory.INTERNAL,
            )
            raise
        self._record_success(
            WhatsAppQueryOperation.CONVERSATION_DETAIL,
            started_at,
            1,
            statements,
        )
        return result

    def _load_summary_relations(
        self,
        conversations: list[WhatsAppConversation],
    ) -> tuple[
        dict[int, WhatsAppConversationOpportunity],
        dict[int | None, tuple[Opportunity, ...]],
        int,
    ]:
        if not conversations:
            return {}, {}, 0
        conversation_ids = tuple(item.id for item in conversations)
        links = self._load_links(conversation_ids, active_only=True)
        customer_ids = tuple(
            item.customer_id
            for item in conversations
            if item.customer_id is not None
            and item.customer is not None
            and item.customer.deleted_at is None
        )
        suggestions = self._load_suggestions(customer_ids)
        statement_count = 1 + (1 if customer_ids else 0)
        return (
            {link.conversation_id: link for link in links},
            suggestions,
            statement_count,
        )

    def _load_links(
        self,
        conversation_ids: tuple[int, ...],
        *,
        active_only: bool = False,
    ) -> list[WhatsAppConversationOpportunity]:
        statement = (
            select(WhatsAppConversationOpportunity)
            .where(
                WhatsAppConversationOpportunity.conversation_id.in_(conversation_ids)
            )
            .options(
                raiseload("*"),
                load_only(
                    WhatsAppConversationOpportunity.id,
                    WhatsAppConversationOpportunity.conversation_id,
                    WhatsAppConversationOpportunity.opportunity_id,
                    WhatsAppConversationOpportunity.linked_at,
                    WhatsAppConversationOpportunity.unlinked_at,
                    WhatsAppConversationOpportunity.linked_by_user_id,
                    WhatsAppConversationOpportunity.link_source,
                    raiseload=True,
                ),
                joinedload(WhatsAppConversationOpportunity.opportunity).load_only(
                    Opportunity.id,
                    Opportunity.status,
                    Opportunity.source,
                    Opportunity.created_at,
                    Opportunity.deleted_at,
                    raiseload=True,
                ),
                joinedload(WhatsAppConversationOpportunity.linked_by_user).load_only(
                    User.id,
                    User.full_name,
                    User.role,
                    raiseload=True,
                ),
            )
            .order_by(
                WhatsAppConversationOpportunity.linked_at,
                WhatsAppConversationOpportunity.id,
            )
        )
        if active_only:
            statement = statement.where(
                WhatsAppConversationOpportunity.unlinked_at.is_(None)
            )
        return list(self._session.scalars(statement))

    def _load_suggestions(
        self,
        customer_ids: tuple[int, ...],
    ) -> dict[int | None, tuple[Opportunity, ...]]:
        if not customer_ids:
            return {}
        opportunities = self._session.scalars(
            select(Opportunity)
            .where(
                Opportunity.customer_id.in_(customer_ids),
                Opportunity.status.in_(_OPEN_OPPORTUNITY_STATUSES),
                Opportunity.deleted_at.is_(None),
            )
            .options(
                raiseload("*"),
                load_only(
                    Opportunity.id,
                    Opportunity.customer_id,
                    Opportunity.status,
                    Opportunity.source,
                    Opportunity.created_at,
                    Opportunity.deleted_at,
                    raiseload=True,
                ),
            )
            .order_by(
                Opportunity.customer_id,
                Opportunity.created_at.desc(),
                Opportunity.id.desc(),
            )
        )
        grouped: defaultdict[int | None, list[Opportunity]] = defaultdict(list)
        for opportunity in opportunities:
            grouped[opportunity.customer_id].append(opportunity)
        return {
            customer_id: tuple(customer_opportunities)
            for customer_id, customer_opportunities in grouped.items()
        }

    def _summary_projection(
        self,
        conversation: WhatsAppConversation,
        resource_updated_at: datetime,
        active_link: WhatsAppConversationOpportunity | None,
        suggestions: tuple[Opportunity, ...],
    ) -> ConversationSummaryProjection:
        try:
            return ConversationSummaryProjection(
                id=conversation.id,
                external_phone=conversation.external_phone,
                display_name=conversation.display_name,
                resolution_status=conversation.resolution_status,
                customer=_customer_projection(conversation.customer),
                active_opportunity=(
                    _opportunity_projection(
                        active_link.opportunity,
                        linked_at=active_link.linked_at,
                    )
                    if active_link is not None
                    else None
                ),
                opportunity_suggestions=tuple(
                    _opportunity_projection(opportunity, linked_at=None)
                    for opportunity in suggestions
                ),
                last_message_at=conversation.last_message_at,
                last_inbound_at=conversation.last_inbound_at,
                last_outbound_at=conversation.last_outbound_at,
                unread_count=conversation.unread_count,
                waiting_for_response=conversation.waiting_for_response,
                waiting_since_at=conversation.waiting_since_at,
                window_expires_at=conversation.window_expires_at,
                updated_at=conversation.updated_at,
                resource_updated_at=resource_updated_at,
            )
        except Exception:
            self._metrics.record_projection_mapping_error(
                WhatsAppProjectionType.CONVERSATION_SUMMARY
            )
            raise

    def _link_projection(
        self,
        link: WhatsAppConversationOpportunity,
        customer: Customer | None,
    ) -> OpportunityLinkProjection:
        try:
            customer_available = customer is not None and customer.deleted_at is None
            return OpportunityLinkProjection(
                id=link.id,
                opportunity=_opportunity_projection(
                    link.opportunity,
                    linked_at=link.linked_at,
                ),
                linked_at=link.linked_at,
                unlinked_at=link.unlinked_at,
                linked_by=_user_projection(link.linked_by_user),
                link_source=link.link_source,
                is_active=link.unlinked_at is None,
                is_actionable=(
                    link.unlinked_at is None
                    and link.opportunity.deleted_at is None
                    and customer_available
                ),
            )
        except Exception:
            self._metrics.record_projection_mapping_error(
                WhatsAppProjectionType.CONVERSATION_DETAIL
            )
            raise

    @staticmethod
    def _snapshot(
        cursor: ConversationPageCursor | None,
        requested_snapshot: datetime | None,
    ) -> datetime:
        if cursor is not None:
            return _aware_utc(cursor.snapshot_at)
        return _aware_utc(requested_snapshot or datetime.now(UTC))

    def _record_success(
        self,
        operation: WhatsAppQueryOperation,
        started_at: float,
        rows: int,
        statements: int,
    ) -> None:
        self._metrics.record_query(
            QueryMeasurement(
                operation=operation,
                outcome=WhatsAppQueryOutcome.SUCCESS,
                duration_seconds=perf_counter() - started_at,
                rows_returned=rows,
                db_statements=statements,
            )
        )

    def _record_failure(
        self,
        operation: WhatsAppQueryOperation,
        started_at: float,
        statements: int,
        category: WhatsAppQueryErrorCategory,
    ) -> None:
        self._metrics.record_query(
            QueryMeasurement(
                operation=operation,
                outcome=WhatsAppQueryOutcome.ERROR,
                duration_seconds=perf_counter() - started_at,
                rows_returned=0,
                db_statements=statements,
            )
        )
        self._metrics.record_error(QueryErrorMeasurement(operation, category))


class MessageQueryService:
    def __init__(
        self,
        session: Session,
        metrics: WhatsAppQueryMetrics | None = None,
    ) -> None:
        self._session = session
        self._metrics = metrics or NullWhatsAppQueryMetrics()

    def list_message_history(
        self,
        conversation_id: int,
        page: MessagePageRequest,
        *,
        snapshot_at: datetime | None = None,
    ) -> MessagePage:
        started_at = perf_counter()
        snapshot = (
            _aware_utc(page.before.snapshot_at)
            if page.before is not None
            else _aware_utc(snapshot_at or datetime.now(UTC))
        )
        message_at = _message_at()
        change_key = _message_change_key()
        filters: list[ColumnElement[bool]] = [
            WhatsAppMessage.conversation_id == conversation_id,
            change_key <= snapshot,
        ]
        if page.before is not None:
            filters.append(
                or_(
                    message_at < page.before.message_at,
                    and_(
                        message_at == page.before.message_at,
                        WhatsAppMessage.id < page.before.message_id,
                    ),
                )
            )
        statement = (
            select(WhatsAppMessage, message_at, change_key)
            .where(*filters)
            .options(
                raiseload("*"),
                *_message_load_options(),
            )
            .order_by(message_at.desc(), WhatsAppMessage.id.desc())
            .limit(page.limit + 1)
        )
        try:
            with self._session.no_autoflush:
                conversation_exists = self._session.scalar(
                    select(WhatsAppConversation.id).where(
                        WhatsAppConversation.id == conversation_id
                    )
                )
                statements = 1
                _require_entity(
                    conversation_exists,
                    "WhatsAppConversation",
                    conversation_id,
                )
                rows = list(self._session.execute(statement).tuples())
                statements += 1
                has_more = len(rows) > page.limit
                selected_rows = rows[: page.limit]
                items = tuple(
                    reversed(
                        tuple(
                            self._message_projection(message, at, changed_at)
                            for message, at, changed_at in selected_rows
                        )
                    )
                )
            next_cursor = (
                MessagePageCursor(
                    snapshot_at=snapshot,
                    message_at=items[0].message_at,
                    message_id=items[0].id,
                )
                if has_more and items
                else None
            )
            result = MessagePage(
                items=items,
                next_before_cursor=next_cursor,
                sync_cursor=ResourceChangeCursor(snapshot, _MAX_BIGINT),
            )
        except EntityNotFoundError:
            self._record_failure(
                WhatsAppQueryOperation.MESSAGE_HISTORY,
                started_at,
                1,
                WhatsAppQueryErrorCategory.NOT_FOUND,
            )
            raise
        except Exception:
            self._record_failure(
                WhatsAppQueryOperation.MESSAGE_HISTORY,
                started_at,
                1,
                WhatsAppQueryErrorCategory.INTERNAL,
            )
            raise
        self._record_success(
            WhatsAppQueryOperation.MESSAGE_HISTORY,
            started_at,
            len(result.items),
            statements,
        )
        return result

    def get_message(self, message_id: int) -> MessageProjection:
        started_at = perf_counter()
        message_at = _message_at()
        change_key = _message_change_key()
        statement = (
            select(WhatsAppMessage, message_at, change_key)
            .where(WhatsAppMessage.id == message_id)
            .options(
                raiseload("*"),
                *_message_load_options(),
            )
        )
        try:
            with self._session.no_autoflush:
                row = self._session.execute(statement).tuples().one_or_none()
                message, at, changed_at = _require_entity(
                    row,
                    "WhatsAppMessage",
                    message_id,
                )
                result = self._message_projection(message, at, changed_at)
        except EntityNotFoundError:
            self._record_failure(
                WhatsAppQueryOperation.MESSAGE_HISTORY,
                started_at,
                1,
                WhatsAppQueryErrorCategory.NOT_FOUND,
            )
            raise
        except Exception:
            self._record_failure(
                WhatsAppQueryOperation.MESSAGE_HISTORY,
                started_at,
                1,
                WhatsAppQueryErrorCategory.INTERNAL,
            )
            raise
        self._record_success(
            WhatsAppQueryOperation.MESSAGE_HISTORY,
            started_at,
            1,
            1,
        )
        return result

    def list_message_changes(
        self,
        conversation_id: int,
        page: ChangePageRequest,
    ) -> MessageChangePage:
        return PollingQueryService(
            self._session,
            self._metrics,
        ).list_message_changes(conversation_id, page)

    def _message_projection(
        self,
        message: WhatsAppMessage,
        message_at: datetime,
        resource_updated_at: datetime,
    ) -> MessageProjection:
        try:
            attachment = message.attachment
            attachment_projection = (
                _attachment_projection(attachment) if attachment is not None else None
            )
            return MessageProjection(
                id=message.id,
                conversation_id=message.conversation_id,
                external_message_id=message.external_message_id,
                client_generated_id=message.client_generated_id,
                direction=message.direction,
                message_type=message.message_type,
                body=message.body,
                sent_by=_user_projection(message.sent_by_user),
                retry_of_message_id=message.retry_of_message_id,
                is_retry=message.retry_of_message_id is not None,
                message_at=message_at,
                attachment=attachment_projection,
                status=MessageStatusProjection(
                    dispatch_state=message.dispatch_state,
                    provider_state=message.provider_state,
                    accepted_at=message.accepted_at,
                    sent_at=message.sent_at,
                    delivered_at=message.delivered_at,
                    read_at=message.read_at,
                    failed_at=message.failed_at,
                    error_code=message.provider_error_code,
                    error_message=message.provider_error_message,
                ),
                created_at=message.created_at,
                updated_at=message.updated_at,
                resource_updated_at=resource_updated_at,
            )
        except Exception:
            self._metrics.record_projection_mapping_error(
                WhatsAppProjectionType.MESSAGE
            )
            raise

    def _record_success(
        self,
        operation: WhatsAppQueryOperation,
        started_at: float,
        rows: int,
        statements: int,
    ) -> None:
        self._metrics.record_query(
            QueryMeasurement(
                operation=operation,
                outcome=WhatsAppQueryOutcome.SUCCESS,
                duration_seconds=perf_counter() - started_at,
                rows_returned=rows,
                db_statements=statements,
            )
        )

    def _record_failure(
        self,
        operation: WhatsAppQueryOperation,
        started_at: float,
        statements: int,
        category: WhatsAppQueryErrorCategory,
    ) -> None:
        self._metrics.record_query(
            QueryMeasurement(
                operation=operation,
                outcome=WhatsAppQueryOutcome.ERROR,
                duration_seconds=perf_counter() - started_at,
                rows_returned=0,
                db_statements=statements,
            )
        )
        self._metrics.record_error(QueryErrorMeasurement(operation, category))


class PollingQueryService:
    def __init__(
        self,
        session: Session,
        metrics: WhatsAppQueryMetrics | None = None,
    ) -> None:
        self._session = session
        self._metrics = metrics or NullWhatsAppQueryMetrics()

    def list_conversation_changes(
        self,
        page: ChangePageRequest,
    ) -> ConversationChangePage:
        started_at = perf_counter()
        statements = 0
        change_key = _conversation_change_key()
        statement = (
            select(WhatsAppConversation, change_key.label("resource_updated_at"))
            .outerjoin(Customer, Customer.id == WhatsAppConversation.customer_id)
            .where(_after_change_cursor(change_key, WhatsAppConversation.id, page))
            .options(
                raiseload("*"),
                load_only(
                    WhatsAppConversation.id,
                    WhatsAppConversation.customer_id,
                    WhatsAppConversation.external_phone,
                    WhatsAppConversation.display_name,
                    WhatsAppConversation.resolution_status,
                    WhatsAppConversation.last_message_at,
                    WhatsAppConversation.last_inbound_at,
                    WhatsAppConversation.last_outbound_at,
                    WhatsAppConversation.unread_count,
                    WhatsAppConversation.waiting_for_response,
                    WhatsAppConversation.waiting_since_at,
                    WhatsAppConversation.window_expires_at,
                    WhatsAppConversation.created_at,
                    WhatsAppConversation.updated_at,
                    raiseload=True,
                ),
                joinedload(WhatsAppConversation.customer).load_only(
                    Customer.id,
                    Customer.name,
                    Customer.company,
                    Customer.phone,
                    Customer.province,
                    Customer.deleted_at,
                    raiseload=True,
                ),
            )
            .order_by(change_key, WhatsAppConversation.id)
            .limit(page.limit + 1)
        )
        conversation_queries = ConversationQueryService(
            self._session,
            self._metrics,
        )
        try:
            with self._session.no_autoflush:
                rows = list(self._session.execute(statement).tuples())
                statements += 1
                has_more = len(rows) > page.limit
                selected_rows = rows[: page.limit]
                conversations = [row[0] for row in selected_rows]
                active_links, suggestions, relation_statements = (
                    conversation_queries._load_summary_relations(conversations)
                )
                statements += relation_statements
                items = tuple(
                    conversation_queries._summary_projection(
                        conversation,
                        changed_at,
                        active_links.get(conversation.id),
                        suggestions.get(conversation.customer_id, ()),
                    )
                    for conversation, changed_at in selected_rows
                )
            next_cursor = (
                ResourceChangeCursor(
                    items[-1].resource_updated_at,
                    items[-1].id,
                )
                if items
                else page.cursor
            )
            result = ConversationChangePage(items, next_cursor, has_more)
        except Exception:
            self._record_failure(started_at, statements)
            raise
        self._record_success(started_at, len(result.items), statements)
        return result

    def list_message_changes(
        self,
        conversation_id: int,
        page: ChangePageRequest,
    ) -> MessageChangePage:
        started_at = perf_counter()
        change_key = _message_change_key()
        message_at = _message_at()
        statement = (
            select(WhatsAppMessage, message_at, change_key)
            .where(
                WhatsAppMessage.conversation_id == conversation_id,
                _after_change_cursor(change_key, WhatsAppMessage.id, page),
            )
            .options(
                raiseload("*"),
                *_message_load_options(),
            )
            .order_by(change_key, WhatsAppMessage.id)
            .limit(page.limit + 1)
        )
        message_queries = MessageQueryService(self._session, self._metrics)
        try:
            with self._session.no_autoflush:
                rows = list(self._session.execute(statement).tuples())
                has_more = len(rows) > page.limit
                selected_rows = rows[: page.limit]
                items = tuple(
                    message_queries._message_projection(message, at, changed_at)
                    for message, at, changed_at in selected_rows
                )
            next_cursor = (
                ResourceChangeCursor(
                    items[-1].resource_updated_at,
                    items[-1].id,
                )
                if items
                else page.cursor
            )
            result = MessageChangePage(items, next_cursor, has_more)
        except Exception:
            self._record_failure(started_at, 1)
            raise
        self._record_success(started_at, len(result.items), 1)
        return result

    def _record_success(
        self,
        started_at: float,
        rows: int,
        statements: int,
    ) -> None:
        self._metrics.record_query(
            QueryMeasurement(
                operation=WhatsAppQueryOperation.POLLING,
                outcome=WhatsAppQueryOutcome.SUCCESS,
                duration_seconds=perf_counter() - started_at,
                rows_returned=rows,
                db_statements=statements,
            )
        )

    def _record_failure(self, started_at: float, statements: int) -> None:
        self._metrics.record_query(
            QueryMeasurement(
                operation=WhatsAppQueryOperation.POLLING,
                outcome=WhatsAppQueryOutcome.ERROR,
                duration_seconds=perf_counter() - started_at,
                rows_returned=0,
                db_statements=statements,
            )
        )
        self._metrics.record_error(
            QueryErrorMeasurement(
                WhatsAppQueryOperation.POLLING,
                WhatsAppQueryErrorCategory.INTERNAL,
            )
        )


def _message_load_options() -> tuple[ExecutableOption, ...]:
    return (
        load_only(
            WhatsAppMessage.id,
            WhatsAppMessage.conversation_id,
            WhatsAppMessage.external_message_id,
            WhatsAppMessage.client_generated_id,
            WhatsAppMessage.direction,
            WhatsAppMessage.message_type,
            WhatsAppMessage.body,
            WhatsAppMessage.sent_by_user_id,
            WhatsAppMessage.retry_of_message_id,
            WhatsAppMessage.dispatch_state,
            WhatsAppMessage.provider_state,
            WhatsAppMessage.provider_error_code,
            WhatsAppMessage.provider_error_message,
            WhatsAppMessage.provider_message_at,
            WhatsAppMessage.accepted_at,
            WhatsAppMessage.sent_at,
            WhatsAppMessage.delivered_at,
            WhatsAppMessage.read_at,
            WhatsAppMessage.failed_at,
            WhatsAppMessage.created_at,
            WhatsAppMessage.updated_at,
            raiseload=True,
        ),
        joinedload(WhatsAppMessage.sent_by_user).load_only(
            User.id,
            User.full_name,
            User.role,
            raiseload=True,
        ),
        joinedload(WhatsAppMessage.attachment).load_only(
            WhatsAppAttachment.id,
            WhatsAppAttachment.media_type,
            WhatsAppAttachment.mime_type,
            WhatsAppAttachment.filename,
            WhatsAppAttachment.size_bytes,
            WhatsAppAttachment.storage_status,
            raiseload=True,
        ),
    )


def _conversation_change_key() -> ColumnElement[datetime]:
    link_change = (
        select(
            func.max(
                func.greatest(
                    WhatsAppConversationOpportunity.linked_at,
                    func.coalesce(
                        WhatsAppConversationOpportunity.unlinked_at,
                        WhatsAppConversationOpportunity.linked_at,
                    ),
                )
            )
        )
        .where(
            WhatsAppConversationOpportunity.conversation_id == WhatsAppConversation.id
        )
        .correlate(WhatsAppConversation)
        .scalar_subquery()
    )
    opportunity_change = (
        select(func.max(Opportunity.updated_at))
        .where(Opportunity.customer_id == WhatsAppConversation.customer_id)
        .correlate(WhatsAppConversation)
        .scalar_subquery()
    )
    return func.greatest(
        WhatsAppConversation.updated_at,
        func.coalesce(Customer.updated_at, WhatsAppConversation.updated_at),
        func.coalesce(link_change, WhatsAppConversation.updated_at),
        func.coalesce(opportunity_change, WhatsAppConversation.updated_at),
    )


def _message_change_key() -> ColumnElement[datetime]:
    attachment_change = (
        select(func.max(WhatsAppAttachment.updated_at))
        .where(WhatsAppAttachment.message_id == WhatsAppMessage.id)
        .correlate(WhatsAppMessage)
        .scalar_subquery()
    )
    status_change = (
        select(
            func.max(
                func.greatest(
                    WhatsAppMessageStatusEvent.occurred_at,
                    WhatsAppMessageStatusEvent.received_at,
                )
            )
        )
        .where(WhatsAppMessageStatusEvent.message_id == WhatsAppMessage.id)
        .correlate(WhatsAppMessage)
        .scalar_subquery()
    )
    return func.greatest(
        WhatsAppMessage.updated_at,
        func.coalesce(attachment_change, WhatsAppMessage.updated_at),
        func.coalesce(status_change, WhatsAppMessage.updated_at),
    )


def _message_at() -> ColumnElement[datetime]:
    return func.coalesce(
        WhatsAppMessage.provider_message_at,
        WhatsAppMessage.accepted_at,
        WhatsAppMessage.created_at,
    )


def _conversation_order() -> tuple[
    UnaryExpression[int],
    UnaryExpression[int],
    UnaryExpression[datetime | None],
    UnaryExpression[int],
]:
    waiting_rank: Case[int] = case(
        (WhatsAppConversation.waiting_for_response.is_(True), 1),
        else_=0,
    )
    return (
        waiting_rank.desc(),
        WhatsAppConversation.unread_count.desc(),
        WhatsAppConversation.last_message_at.desc().nullslast(),
        WhatsAppConversation.id.desc(),
    )


def _conversation_after_cursor(
    cursor: ConversationPageCursor,
) -> ColumnElement[bool]:
    waiting_rank = case(
        (WhatsAppConversation.waiting_for_response.is_(True), 1),
        else_=0,
    )
    cursor_waiting_rank = 1 if cursor.waiting_for_response else 0
    same_waiting = waiting_rank == cursor_waiting_rank
    same_unread = WhatsAppConversation.unread_count == cursor.unread_count
    if cursor.last_message_at is None:
        after_last_message = and_(
            WhatsAppConversation.last_message_at.is_(None),
            WhatsAppConversation.id < cursor.conversation_id,
        )
    else:
        after_last_message = or_(
            WhatsAppConversation.last_message_at < cursor.last_message_at,
            WhatsAppConversation.last_message_at.is_(None),
            and_(
                WhatsAppConversation.last_message_at == cursor.last_message_at,
                WhatsAppConversation.id < cursor.conversation_id,
            ),
        )
    return or_(
        waiting_rank < cursor_waiting_rank,
        and_(same_waiting, WhatsAppConversation.unread_count < cursor.unread_count),
        and_(same_waiting, same_unread, after_last_message),
    )


def _conversation_cursor(
    item: ConversationSummaryProjection,
    snapshot: datetime,
) -> ConversationPageCursor:
    return ConversationPageCursor(
        snapshot_at=snapshot,
        waiting_for_response=item.waiting_for_response,
        unread_count=item.unread_count,
        last_message_at=item.last_message_at,
        conversation_id=item.id,
    )


def _conversation_search_filter(search: str | None) -> ColumnElement[bool] | None:
    if search is None:
        return None
    trimmed = search.strip()
    if not trimmed:
        return None
    escaped = trimmed.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    filters: list[ColumnElement[bool]] = [
        WhatsAppConversation.display_name.ilike(pattern, escape="\\"),
        Customer.name.ilike(pattern, escape="\\"),
        Customer.company.ilike(pattern, escape="\\"),
    ]
    phone = comparable_phone(trimmed)
    if phone is not None:
        filters.append(WhatsAppConversation.phone_match_key.contains(phone))
    return or_(*filters)


def _after_change_cursor(
    change_key: ColumnElement[datetime],
    resource_id: InstrumentedAttribute[int],
    page: ChangePageRequest,
) -> ColumnElement[bool]:
    return or_(
        change_key > page.cursor.resource_updated_at,
        and_(
            change_key == page.cursor.resource_updated_at,
            resource_id > page.cursor.resource_id,
        ),
    )


def _customer_projection(
    customer: Customer | None,
) -> CustomerSummaryProjection | None:
    if customer is None:
        return None
    return CustomerSummaryProjection(
        id=customer.id,
        name=customer.name,
        company=customer.company,
        phone=customer.phone,
        province=customer.province,
        is_available=customer.deleted_at is None,
    )


def _user_projection(user: User | None) -> UserSummaryProjection | None:
    if user is None:
        return None
    return UserSummaryProjection(
        id=user.id,
        full_name=user.full_name,
        role=user.role,
    )


def _opportunity_projection(
    opportunity: Opportunity,
    *,
    linked_at: datetime | None,
) -> OpportunitySummaryProjection:
    return OpportunitySummaryProjection(
        id=opportunity.id,
        status=opportunity.status,
        source=opportunity.source,
        created_at=opportunity.created_at,
        linked_at=linked_at,
        is_open=opportunity.status in _OPEN_OPPORTUNITY_STATUSES,
        is_available=opportunity.deleted_at is None,
    )


def _attachment_projection(
    attachment: WhatsAppAttachment,
) -> AttachmentProjection:
    available = attachment.storage_status is WhatsAppStorageStatus.AVAILABLE
    return AttachmentProjection(
        id=attachment.id,
        media_type=attachment.media_type,
        mime_type=attachment.mime_type,
        filename=_sanitized_filename(attachment.filename),
        size_bytes=attachment.size_bytes,
        is_available=available,
        content_reference=(
            AttachmentContentReference(attachment.id) if available else None
        ),
    )


def _sanitized_filename(filename: str | None) -> str | None:
    if filename is None:
        return None
    leaf = PurePath(filename.replace("\\", "/")).name
    cleaned = "".join(
        character for character in leaf if character.isprintable()
    ).strip()
    return cleaned or None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware")
    return value.astimezone(UTC)


def _require_entity[EntityValue](
    value: EntityValue | None,
    entity_name: str,
    entity_id: int,
) -> EntityValue:
    if value is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return value
