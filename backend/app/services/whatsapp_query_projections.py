from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.models import (
    LeadSource,
    OpportunityStatus,
    UserRole,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessageType,
    WhatsAppOpportunityLinkSource,
    WhatsAppProviderState,
)


@dataclass(frozen=True, slots=True)
class CustomerSummaryProjection:
    id: int
    name: str
    company: str | None
    phone: str | None
    province: str | None
    is_available: bool


@dataclass(frozen=True, slots=True)
class UserSummaryProjection:
    id: int
    full_name: str
    role: UserRole


@dataclass(frozen=True, slots=True)
class OpportunitySummaryProjection:
    id: int
    status: OpportunityStatus
    source: LeadSource
    created_at: datetime
    linked_at: datetime | None
    is_open: bool
    is_available: bool


@dataclass(frozen=True, slots=True)
class OpportunityLinkProjection:
    id: int
    opportunity: OpportunitySummaryProjection
    linked_at: datetime
    unlinked_at: datetime | None
    linked_by: UserSummaryProjection | None
    link_source: WhatsAppOpportunityLinkSource
    is_active: bool
    is_actionable: bool


@dataclass(frozen=True, slots=True)
class ConversationSummaryProjection:
    id: int
    external_phone: str
    display_name: str | None
    resolution_status: WhatsAppConversationResolution
    customer: CustomerSummaryProjection | None
    active_opportunity: OpportunitySummaryProjection | None
    opportunity_suggestions: tuple[OpportunitySummaryProjection, ...]
    last_message_at: datetime | None
    last_inbound_at: datetime | None
    last_outbound_at: datetime | None
    unread_count: int
    waiting_for_response: bool
    waiting_since_at: datetime | None
    window_expires_at: datetime | None
    updated_at: datetime
    resource_updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationDetailProjection:
    summary: ConversationSummaryProjection
    opportunity_links: tuple[OpportunityLinkProjection, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AttachmentContentReference:
    attachment_id: int


@dataclass(frozen=True, slots=True)
class AttachmentProjection:
    id: int
    media_type: WhatsAppMessageType
    mime_type: str | None
    filename: str | None
    size_bytes: int | None
    is_available: bool
    content_reference: AttachmentContentReference | None


@dataclass(frozen=True, slots=True)
class MessageStatusProjection:
    dispatch_state: WhatsAppDispatchState | None
    provider_state: WhatsAppProviderState | None
    accepted_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class MessageProjection:
    id: int
    conversation_id: int
    external_message_id: str | None
    client_generated_id: UUID | None
    direction: WhatsAppDirection
    message_type: WhatsAppMessageType
    body: str | None
    sent_by: UserSummaryProjection | None
    retry_of_message_id: int | None
    is_retry: bool
    message_at: datetime
    attachment: AttachmentProjection | None
    status: MessageStatusProjection
    created_at: datetime
    updated_at: datetime
    resource_updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationListFilters:
    waiting_only: bool = False
    unread_only: bool = False
    search: str | None = None


@dataclass(frozen=True, slots=True)
class ConversationPageCursor:
    snapshot_at: datetime
    waiting_for_response: bool
    unread_count: int
    last_message_at: datetime | None
    conversation_id: int


@dataclass(frozen=True, slots=True)
class MessagePageCursor:
    snapshot_at: datetime
    message_at: datetime
    message_id: int


@dataclass(frozen=True, slots=True)
class ResourceChangeCursor:
    resource_updated_at: datetime
    resource_id: int


@dataclass(frozen=True, slots=True)
class ConversationPageRequest:
    limit: int = 50
    cursor: ConversationPageCursor | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 50:
            raise ValueError("Conversation page limit must be between 1 and 50")


@dataclass(frozen=True, slots=True)
class MessagePageRequest:
    limit: int = 100
    before: MessagePageCursor | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 100:
            raise ValueError("Message page limit must be between 1 and 100")


@dataclass(frozen=True, slots=True)
class ChangePageRequest:
    cursor: ResourceChangeCursor
    limit: int = 500

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 500:
            raise ValueError("Change page limit must be between 1 and 500")


@dataclass(frozen=True, slots=True)
class ConversationPage:
    items: tuple[ConversationSummaryProjection, ...]
    next_cursor: ConversationPageCursor | None
    sync_cursor: ResourceChangeCursor


@dataclass(frozen=True, slots=True)
class MessagePage:
    items: tuple[MessageProjection, ...]
    next_before_cursor: MessagePageCursor | None
    sync_cursor: ResourceChangeCursor


@dataclass(frozen=True, slots=True)
class ConversationChangePage:
    items: tuple[ConversationSummaryProjection, ...]
    next_cursor: ResourceChangeCursor
    has_more: bool


@dataclass(frozen=True, slots=True)
class MessageChangePage:
    items: tuple[MessageProjection, ...]
    next_cursor: ResourceChangeCursor
    has_more: bool
