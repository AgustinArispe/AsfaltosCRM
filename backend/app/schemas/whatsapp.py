from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from app.models import (
    LeadSource,
    OpportunityStatus,
    UserRole,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessageOrigin,
    WhatsAppMessageType,
    WhatsAppOpportunityLinkSource,
    WhatsAppProviderState,
)
from app.schemas.common import StrictRequestModel
from app.whatsapp import ProviderErrorKind, TemplateHeaderType

PositiveId = Annotated[int, Field(gt=0)]
NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
OptionalShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class WhatsAppWindowReason(StrEnum):
    APPROVED_TEMPLATE_REQUIRED = "APPROVED_TEMPLATE_REQUIRED"


class CustomerSummaryResponse(BaseModel):
    id: int
    name: str
    company: str | None
    phone: str | None
    province: str | None
    is_available: bool


class UserSummaryResponse(BaseModel):
    id: int
    full_name: str
    role: UserRole


class OpportunitySummaryResponse(BaseModel):
    id: int
    status: OpportunityStatus
    source: LeadSource
    created_at: datetime
    linked_at: datetime | None
    is_open: bool
    is_available: bool


class OpportunityLinkResponse(BaseModel):
    id: int
    opportunity: OpportunitySummaryResponse
    linked_at: datetime
    unlinked_at: datetime | None
    linked_by: UserSummaryResponse | None
    link_source: WhatsAppOpportunityLinkSource
    is_active: bool
    is_actionable: bool


class ConversationSummaryResponse(BaseModel):
    id: int
    external_phone: str
    display_name: str | None
    resolution_status: WhatsAppConversationResolution
    customer: CustomerSummaryResponse | None
    active_opportunity: OpportunitySummaryResponse | None
    opportunity_suggestions: list[OpportunitySummaryResponse]
    last_message_at: datetime | None
    last_inbound_at: datetime | None
    last_outbound_at: datetime | None
    unread_count: int
    waiting_for_response: bool
    waiting_since_at: datetime | None
    can_send_freeform: bool
    window_expires_at: datetime | None
    template_required: bool
    reason: WhatsAppWindowReason | None
    updated_at: datetime
    resource_updated_at: datetime


class ConversationDetailResponse(ConversationSummaryResponse):
    opportunity_links: list[OpportunityLinkResponse]
    created_at: datetime


class ConversationPageResponse(BaseModel):
    items: list[ConversationSummaryResponse]
    next_page_cursor: str | None
    sync_cursor: str


class ConversationChangePageResponse(BaseModel):
    items: list[ConversationSummaryResponse]
    next_cursor: str
    has_more: bool


class AttachmentResponse(BaseModel):
    id: int
    media_type: WhatsAppMessageType
    mime_type: str | None
    filename: str | None
    size_bytes: int | None
    is_available: bool
    content_url: str | None


class MessageStatusResponse(BaseModel):
    dispatch_state: WhatsAppDispatchState | None
    provider_state: WhatsAppProviderState | None
    accepted_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    error_code: str | None
    error_message: str | None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    external_message_id: str | None
    client_generated_id: UUID | None
    direction: WhatsAppDirection
    message_type: WhatsAppMessageType
    origin: WhatsAppMessageOrigin
    body: str | None
    template_name: str | None
    template_language: str | None
    sent_by: UserSummaryResponse | None
    retry_of_message_id: int | None
    is_retry: bool
    message_at: datetime
    attachment: AttachmentResponse | None
    status: MessageStatusResponse
    created_at: datetime
    updated_at: datetime
    resource_updated_at: datetime


class MessagePageResponse(BaseModel):
    items: list[MessageResponse]
    next_before_cursor: str | None
    sync_cursor: str


class MessageChangePageResponse(BaseModel):
    items: list[MessageResponse]
    next_cursor: str
    has_more: bool


class OutboundMessageResponse(BaseModel):
    message: MessageResponse
    can_send_freeform: bool
    window_expires_at: datetime | None
    template_required: bool
    reason: WhatsAppWindowReason | None


class HumanTemplateResponse(BaseModel):
    name: str
    language: str
    category: str
    parameter_names: list[str]
    header_type: TemplateHeaderType
    header_media_required: bool
    body_preview: None = None


class HumanTemplateParameterRequest(StrictRequestModel):
    name: NonBlankText
    value: NonBlankText


class HumanTemplateSendRequest(StrictRequestModel):
    template_name: NonBlankText
    language: NonBlankText
    parameters: list[HumanTemplateParameterRequest] = Field(default_factory=list)
    header_media_ref: UUID | None = None
    client_generated_id: UUID


class TextOutboundRequest(StrictRequestModel):
    message_type: Literal[WhatsAppMessageType.TEXT]
    client_generated_id: UUID
    body: NonBlankText
    retry_of_message_id: PositiveId | None = None


class ImageOutboundRequest(StrictRequestModel):
    message_type: Literal[WhatsAppMessageType.IMAGE]
    client_generated_id: UUID
    media_ref: UUID
    caption: NonBlankText | None = None
    retry_of_message_id: PositiveId | None = None


class DocumentOutboundRequest(StrictRequestModel):
    message_type: Literal[WhatsAppMessageType.DOCUMENT]
    client_generated_id: UUID
    media_ref: UUID
    caption: NonBlankText | None = None
    retry_of_message_id: PositiveId | None = None


OutboundMessageRequest = Annotated[
    TextOutboundRequest | ImageOutboundRequest | DocumentOutboundRequest,
    Field(discriminator="message_type"),
]


class OpportunityLinkRequest(StrictRequestModel):
    opportunity_id: PositiveId


class MediaUploadMetadata(StrictRequestModel):
    media_type: Literal[
        WhatsAppMessageType.IMAGE,
        WhatsAppMessageType.DOCUMENT,
    ]


class MediaUploadResponse(BaseModel):
    media_ref: UUID
    media_type: WhatsAppMessageType
    mime_type: str
    filename: str | None
    size_bytes: int
    content_url: str


class FakeInboundTextRequest(StrictRequestModel):
    message_type: Literal[WhatsAppMessageType.TEXT]
    external_message_id: NonBlankText
    external_phone: NonBlankText
    provider_contact_id: OptionalShortText | None = None
    display_name: OptionalShortText | None = None
    body: NonBlankText
    provider_message_at: AwareDatetime


class FakeInboundMediaRequest(StrictRequestModel):
    message_type: Literal[
        WhatsAppMessageType.IMAGE,
        WhatsAppMessageType.DOCUMENT,
    ]
    external_message_id: NonBlankText
    external_phone: NonBlankText
    provider_contact_id: OptionalShortText | None = None
    display_name: OptionalShortText | None = None
    caption: NonBlankText | None = None
    media_ref: UUID
    provider_message_at: AwareDatetime


FakeInboundRequest = Annotated[
    FakeInboundTextRequest | FakeInboundMediaRequest,
    Field(discriminator="message_type"),
]


class FakeInboundResponse(BaseModel):
    created: bool
    message: MessageResponse


class FakeDeliveryState(StrEnum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class FakeStatusEventRequest(StrictRequestModel):
    state: FakeDeliveryState
    occurred_at: AwareDatetime
    error_code: OptionalShortText | None = None
    error_message: OptionalShortText | None = None


class FakeStatusSequenceRequest(StrictRequestModel):
    events: Annotated[list[FakeStatusEventRequest], Field(min_length=1)]
    duplicate: bool = False


class FakeStatusResultResponse(BaseModel):
    event_id: int
    message_id: int | None
    created: bool


class FakeStatusSequenceResponse(BaseModel):
    results: list[FakeStatusResultResponse]
    message: MessageResponse


class FakeProviderBehaviorRequest(StrictRequestModel):
    kind: ProviderErrorKind
    code: OptionalShortText | None = None
    safe_message: OptionalShortText = "Fake provider failure"


class FakeProviderBehaviorResponse(BaseModel):
    client_generated_id: UUID
    kind: ProviderErrorKind
