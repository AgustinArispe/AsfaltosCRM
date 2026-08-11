from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from app.models import (
    WhatsAppBroadcastAuditEventType,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppBroadcastStatus,
    WhatsAppConsentDecision,
    WhatsAppConsentSource,
    WhatsAppMessageType,
)
from app.schemas.common import StrictRequestModel
from app.whatsapp import TemplateHeaderType

PositiveId = Annotated[int, Field(gt=0)]
NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
ParameterValue = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1024),
]


class ConsentEventRequest(StrictRequestModel):
    client_event_id: UUID
    customer_id: PositiveId
    decision: WhatsAppConsentDecision
    source: WhatsAppConsentSource
    occurred_at: AwareDatetime
    effective_at: AwareDatetime | None = None
    evidence_reference: NonBlankText | None = None


class ConsentEventResponse(BaseModel):
    id: int
    client_event_id: UUID
    customer_id: int
    normalized_phone: str
    decision: WhatsAppConsentDecision
    source: WhatsAppConsentSource
    evidence_reference: str | None
    occurred_at: datetime
    effective_at: datetime
    recorded_at: datetime
    recorded_by_user_id: int


class ConsentEventResultResponse(BaseModel):
    event: ConsentEventResponse
    current: ConsentEventResponse
    created: bool


class ConsentHistoryResponse(BaseModel):
    items: list[ConsentEventResponse]
    next_cursor: str | None


class BroadcastTemplateResponse(BaseModel):
    external_id: str
    name: str
    language: str
    category: str
    status: str
    header_type: TemplateHeaderType
    parameter_names: list[str]
    header_media_required: bool


class BroadcastParameterRequest(StrictRequestModel):
    name: NonBlankText
    value: ParameterValue


class BroadcastCreateRequest(StrictRequestModel):
    client_generated_id: UUID
    label: NonBlankText
    external_campaign_reference: NonBlankText | None = None
    template_external_id: NonBlankText
    parameters: list[BroadcastParameterRequest] = Field(default_factory=list)
    header_media_ref: UUID | None = None


class BroadcastParameterResponse(BaseModel):
    name: str
    value: str


class BroadcastRecipientResponse(BaseModel):
    id: int
    customer_id: int
    customer_display_name: str
    normalized_phone: str
    consent_event_id: int | None
    status: WhatsAppBroadcastRecipientStatus
    reason_code: str | None
    safe_error_code: str | None
    safe_error_message: str | None
    conversation_id: int | None
    confirmed_at: datetime | None
    first_attempt_at: datetime | None
    latest_attempt_at: datetime | None
    accepted_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BroadcastAuditEventResponse(BaseModel):
    id: int
    command_id: UUID | None
    recipient_id: int | None
    message_id: int | None
    event_type: WhatsAppBroadcastAuditEventType
    reason_code: str | None
    actor_user_id: int | None
    affected_count: int | None
    occurred_at: datetime


class BroadcastResponse(BaseModel):
    id: int
    client_generated_id: UUID
    label: str
    external_campaign_reference: str | None
    status: WhatsAppBroadcastStatus
    version: int
    template_external_id: str
    template_name: str
    template_language: str
    template_category: str
    template_provider_status: str
    template_header_type: WhatsAppMessageType | None
    template_header_media_required: bool
    header_media_ref: UUID | None
    parameters: list[BroadcastParameterResponse]
    recipient_count: int
    created_by_user_id: int
    confirmed_by_user_id: int | None
    started_by_user_id: int | None
    validated_at: datetime | None
    confirmed_at: datetime | None
    started_at: datetime | None
    first_completed_at: datetime | None
    last_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BroadcastDetailResponse(BroadcastResponse):
    recipients: list[BroadcastRecipientResponse]
    audit_events: list[BroadcastAuditEventResponse]


class BroadcastPageResponse(BaseModel):
    items: list[BroadcastResponse]
    next_cursor: str | None


class RecipientSelectionRequest(StrictRequestModel):
    command_id: UUID
    customer_ids: list[PositiveId] = Field(min_length=1)
    expected_version: PositiveId


class RecipientSelectionResponse(BaseModel):
    broadcast_id: int
    version: int
    selected_count: int
    duplicate_customer_ids: list[int]
    invalid_customer_ids: list[int]
    missing_phone_customer_ids: list[int]
    missing_consent_customer_ids: list[int]
    replayed: bool


class BroadcastValidateRequest(StrictRequestModel):
    expected_version: PositiveId


class BroadcastValidationResponse(BaseModel):
    broadcast_id: int
    version: int
    valid: bool
    recipient_count: int
    issues: list[str]
    validation_token: UUID | None
    expires_at: datetime | None


class BroadcastConfirmRequest(StrictRequestModel):
    command_id: UUID
    expected_version: PositiveId
    validation_token: UUID


class BroadcastCommandRequest(StrictRequestModel):
    command_id: UUID


class BroadcastProcessResponse(BaseModel):
    broadcast_id: int
    claimed_count: int
    completed_count: int
    remaining_count: int
    replayed: bool


class BroadcastRetryRequest(StrictRequestModel):
    command_id: UUID
    recipient_ids: list[PositiveId] = Field(min_length=1)


class BroadcastRetryResponse(BaseModel):
    broadcast_id: int
    created_message_ids: list[int]
    rejected_recipient_ids: list[int]
    replayed: bool


class BroadcastStateCountResponse(BaseModel):
    status: WhatsAppBroadcastRecipientStatus
    count: int


class BroadcastReasonCountResponse(BaseModel):
    reason: str
    count: int


class BroadcastDeliverySummaryResponse(BaseModel):
    broadcast_id: int
    recipient_count: int
    message_attempt_count: int
    states: list[BroadcastStateCountResponse]
    reasons: list[BroadcastReasonCountResponse]
    accepted_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    first_completed_at: datetime | None
    last_completed_at: datetime | None
