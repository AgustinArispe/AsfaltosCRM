from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import (
    WhatsAppBroadcast,
    WhatsAppBroadcastAuditEvent,
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastStatus,
    WhatsAppMarketingConsentEvent,
)
from app.schemas.whatsapp_broadcast import (
    BroadcastAuditEventResponse,
    BroadcastCommandRequest,
    BroadcastConfirmRequest,
    BroadcastCreateRequest,
    BroadcastDeliverySummaryResponse,
    BroadcastDetailResponse,
    BroadcastPageResponse,
    BroadcastParameterResponse,
    BroadcastProcessResponse,
    BroadcastReasonCountResponse,
    BroadcastRecipientResponse,
    BroadcastResponse,
    BroadcastRetryRequest,
    BroadcastRetryResponse,
    BroadcastStateCountResponse,
    BroadcastTemplateResponse,
    BroadcastValidateRequest,
    BroadcastValidationResponse,
    ConsentEventRequest,
    ConsentEventResponse,
    ConsentEventResultResponse,
    ConsentHistoryResponse,
    RecipientSelectionRequest,
    RecipientSelectionResponse,
)
from app.services.errors import InvalidWhatsAppBroadcastError
from app.services.whatsapp_broadcast_service import (
    BroadcastCreateInput,
    BroadcastParameterInput,
    WhatsAppBroadcastService,
)
from app.services.whatsapp_consent_service import (
    ConsentEventInput,
    WhatsAppConsentService,
)
from app.whatsapp.runtime import WhatsAppRuntime


def create_whatsapp_broadcast_router(runtime: WhatsAppRuntime) -> APIRouter:
    router = APIRouter(prefix="/whatsapp", tags=["whatsapp-broadcasts"])

    @router.post(
        "/marketing-consent-events",
        response_model=ConsentEventResultResponse,
    )
    def append_consent_event(
        payload: ConsentEventRequest,
        response: Response,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> ConsentEventResultResponse:
        result = WhatsAppConsentService(session).append(
            ConsentEventInput(
                client_event_id=payload.client_event_id,
                customer_id=payload.customer_id,
                decision=payload.decision,
                source=payload.source,
                occurred_at=payload.occurred_at,
                effective_at=payload.effective_at,
                evidence_reference=payload.evidence_reference,
                recorded_by_user_id=current_user.id,
            )
        )
        response.status_code = (
            status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        )
        return ConsentEventResultResponse(
            event=_consent_event(result.event),
            current=_consent_event(result.current),
            created=result.created,
        )

    @router.get(
        "/marketing-consent-events",
        response_model=ConsentHistoryResponse,
    )
    def consent_history(
        customer_id: Annotated[int, Query(gt=0)],
        session: DatabaseSession,
        _current_user: CurrentUser,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ) -> ConsentHistoryResponse:
        items = WhatsAppConsentService(session).history(
            customer_id,
            limit=limit,
            before_id=_decode_cursor(cursor),
        )
        return ConsentHistoryResponse(
            items=[_consent_event(item) for item in items],
            next_cursor=(_encode_cursor(items[-1].id) if len(items) == limit else None),
        )

    @router.get(
        "/broadcast-templates",
        response_model=list[BroadcastTemplateResponse],
    )
    def list_broadcast_templates(
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> list[BroadcastTemplateResponse]:
        return [
            BroadcastTemplateResponse(
                external_id=item.external_id,
                name=item.name,
                language=item.language,
                category=item.category,
                status=item.status,
                header_type=item.header_type,
                parameter_names=list(item.parameter_names),
                header_media_required=item.header_media_required,
            )
            for item in _service(session, runtime).list_templates()
        ]

    @router.post("/broadcasts", response_model=BroadcastResponse)
    def create_broadcast(
        payload: BroadcastCreateRequest,
        response: Response,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> BroadcastResponse:
        broadcast, created = _service(session, runtime).create(
            BroadcastCreateInput(
                client_generated_id=payload.client_generated_id,
                label=payload.label,
                external_campaign_reference=payload.external_campaign_reference,
                template_external_id=payload.template_external_id,
                parameters=tuple(
                    BroadcastParameterInput(item.name, item.value)
                    for item in payload.parameters
                ),
                header_media_ref=payload.header_media_ref,
                created_by_user_id=current_user.id,
            )
        )
        response.status_code = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return _broadcast_response(broadcast)

    @router.get("/broadcasts", response_model=BroadcastPageResponse)
    def list_broadcasts(
        session: DatabaseSession,
        _current_user: CurrentUser,
        broadcast_status: Annotated[
            WhatsAppBroadcastStatus | None,
            Query(alias="status"),
        ] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ) -> BroadcastPageResponse:
        items = _service(session, runtime).list(
            status=broadcast_status,
            limit=limit,
            before_id=_decode_cursor(cursor),
        )
        return BroadcastPageResponse(
            items=[_broadcast_response(item) for item in items],
            next_cursor=(_encode_cursor(items[-1].id) if len(items) == limit else None),
        )

    @router.get("/broadcasts/{broadcast_id}", response_model=BroadcastDetailResponse)
    def get_broadcast(
        broadcast_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> BroadcastDetailResponse:
        return _broadcast_detail(_service(session, runtime).get(broadcast_id))

    @router.put(
        "/broadcasts/{broadcast_id}/recipients",
        response_model=RecipientSelectionResponse,
    )
    def replace_recipients(
        broadcast_id: int,
        payload: RecipientSelectionRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> RecipientSelectionResponse:
        result = _service(session, runtime).replace_recipients(
            broadcast_id,
            command_id=payload.command_id,
            customer_ids=tuple(payload.customer_ids),
            expected_version=payload.expected_version,
            actor_user_id=current_user.id,
        )
        return RecipientSelectionResponse(
            broadcast_id=result.broadcast_id,
            version=result.version,
            selected_count=result.selected_count,
            duplicate_customer_ids=list(result.duplicate_customer_ids),
            invalid_customer_ids=list(result.invalid_customer_ids),
            missing_phone_customer_ids=list(result.missing_phone_customer_ids),
            missing_consent_customer_ids=list(result.missing_consent_customer_ids),
            replayed=result.replayed,
        )

    @router.post(
        "/broadcasts/{broadcast_id}/validate",
        response_model=BroadcastValidationResponse,
    )
    def validate_broadcast(
        broadcast_id: int,
        payload: BroadcastValidateRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> BroadcastValidationResponse:
        result = _service(session, runtime).validate(
            broadcast_id,
            expected_version=payload.expected_version,
            actor_user_id=current_user.id,
        )
        return BroadcastValidationResponse(
            broadcast_id=result.broadcast_id,
            version=result.version,
            valid=result.valid,
            recipient_count=result.recipient_count,
            issues=list(result.issues),
            validation_token=result.validation_token,
            expires_at=result.expires_at,
        )

    @router.post(
        "/broadcasts/{broadcast_id}/confirm",
        response_model=BroadcastResponse,
    )
    def confirm_broadcast(
        broadcast_id: int,
        payload: BroadcastConfirmRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> BroadcastResponse:
        broadcast = _service(session, runtime).confirm(
            broadcast_id,
            command_id=payload.command_id,
            expected_version=payload.expected_version,
            validation_token=payload.validation_token,
            actor_user_id=current_user.id,
        )
        return _broadcast_response(broadcast)

    @router.post(
        "/broadcasts/{broadcast_id}/start",
        response_model=BroadcastResponse,
    )
    def start_broadcast(
        broadcast_id: int,
        payload: BroadcastCommandRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> BroadcastResponse:
        return _broadcast_response(
            _service(session, runtime).start(
                broadcast_id,
                command_id=payload.command_id,
                actor_user_id=current_user.id,
            )
        )

    @router.post(
        "/broadcasts/{broadcast_id}/process",
        response_model=BroadcastProcessResponse,
    )
    def process_broadcast(
        broadcast_id: int,
        payload: BroadcastCommandRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> BroadcastProcessResponse:
        result = _service(session, runtime).process_batch(
            broadcast_id,
            command_id=payload.command_id,
            actor_user_id=current_user.id,
        )
        return BroadcastProcessResponse(
            broadcast_id=result.broadcast_id,
            claimed_count=result.claimed_count,
            completed_count=result.completed_count,
            remaining_count=result.remaining_count,
            replayed=result.replayed,
        )

    @router.post(
        "/broadcasts/{broadcast_id}/retries",
        response_model=BroadcastRetryResponse,
    )
    def retry_broadcast(
        broadcast_id: int,
        payload: BroadcastRetryRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> BroadcastRetryResponse:
        result = _service(session, runtime).retry_failed(
            broadcast_id,
            command_id=payload.command_id,
            recipient_ids=tuple(payload.recipient_ids),
            actor_user_id=current_user.id,
        )
        return BroadcastRetryResponse(
            broadcast_id=result.broadcast_id,
            created_message_ids=list(result.created_message_ids),
            rejected_recipient_ids=list(result.rejected_recipient_ids),
            replayed=result.replayed,
        )

    @router.get(
        "/broadcasts/{broadcast_id}/delivery-summary",
        response_model=BroadcastDeliverySummaryResponse,
    )
    def delivery_summary(
        broadcast_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> BroadcastDeliverySummaryResponse:
        summary = _service(session, runtime).delivery_summary(broadcast_id)
        return BroadcastDeliverySummaryResponse(
            broadcast_id=summary.broadcast_id,
            recipient_count=summary.recipient_count,
            message_attempt_count=summary.message_attempt_count,
            states=[
                BroadcastStateCountResponse(status=item.status, count=item.count)
                for item in summary.states
            ],
            reasons=[
                BroadcastReasonCountResponse(reason=item.reason, count=item.count)
                for item in summary.reasons
            ],
            accepted_at=summary.accepted_at,
            sent_at=summary.sent_at,
            delivered_at=summary.delivered_at,
            read_at=summary.read_at,
            failed_at=summary.failed_at,
            first_completed_at=summary.first_completed_at,
            last_completed_at=summary.last_completed_at,
        )

    return router


def _service(
    session: DatabaseSession,
    runtime: WhatsAppRuntime,
) -> WhatsAppBroadcastService:
    return WhatsAppBroadcastService(
        session,
        runtime.provider,
        runtime.storage,
        batch_size=runtime.broadcast_batch_size,
        claim_timeout=runtime.broadcast_claim_timeout,
    )


def _consent_event(event: WhatsAppMarketingConsentEvent) -> ConsentEventResponse:
    return ConsentEventResponse(
        id=event.id,
        client_event_id=event.client_event_id,
        customer_id=event.customer_id,
        normalized_phone=event.normalized_phone,
        decision=event.decision,
        source=event.source,
        evidence_reference=event.evidence_reference,
        occurred_at=event.occurred_at,
        effective_at=event.effective_at,
        recorded_at=event.recorded_at,
        recorded_by_user_id=event.recorded_by_user_id,
    )


def _broadcast_response(broadcast: WhatsAppBroadcast) -> BroadcastResponse:
    return BroadcastResponse(
        id=broadcast.id,
        client_generated_id=broadcast.client_generated_id,
        label=broadcast.label,
        external_campaign_reference=broadcast.external_campaign_reference,
        status=broadcast.status,
        version=broadcast.version,
        template_external_id=broadcast.template_external_id,
        template_name=broadcast.template_name,
        template_language=broadcast.template_language,
        template_category=broadcast.template_category,
        template_provider_status=broadcast.template_provider_status,
        template_header_type=broadcast.template_header_type,
        template_header_media_required=broadcast.template_header_media_required,
        header_media_ref=broadcast.header_media_ref,
        parameters=[
            BroadcastParameterResponse(name=item.name, value=item.value)
            for item in broadcast.parameters
        ],
        recipient_count=len(broadcast.recipients),
        created_by_user_id=broadcast.created_by_user_id,
        confirmed_by_user_id=broadcast.confirmed_by_user_id,
        started_by_user_id=broadcast.started_by_user_id,
        validated_at=broadcast.validated_at,
        confirmed_at=broadcast.confirmed_at,
        started_at=broadcast.started_at,
        first_completed_at=broadcast.first_completed_at,
        last_completed_at=broadcast.last_completed_at,
        created_at=broadcast.created_at,
        updated_at=broadcast.updated_at,
    )


def _broadcast_detail(broadcast: WhatsAppBroadcast) -> BroadcastDetailResponse:
    summary = _broadcast_response(broadcast)
    return BroadcastDetailResponse(
        **summary.model_dump(),
        recipients=[_recipient(item) for item in broadcast.recipients],
        audit_events=[_audit_event(item) for item in broadcast.audit_events],
    )


def _recipient(recipient: WhatsAppBroadcastRecipient) -> BroadcastRecipientResponse:
    return BroadcastRecipientResponse(
        id=recipient.id,
        customer_id=recipient.customer_id,
        customer_display_name=recipient.customer_display_name,
        normalized_phone=recipient.normalized_phone,
        consent_event_id=recipient.consent_event_id,
        status=recipient.status,
        reason_code=recipient.reason_code,
        safe_error_code=recipient.safe_error_code,
        safe_error_message=recipient.safe_error_message,
        conversation_id=recipient.conversation_id,
        confirmed_at=recipient.confirmed_at,
        first_attempt_at=recipient.first_attempt_at,
        latest_attempt_at=recipient.latest_attempt_at,
        accepted_at=recipient.accepted_at,
        sent_at=recipient.sent_at,
        delivered_at=recipient.delivered_at,
        read_at=recipient.read_at,
        failed_at=recipient.failed_at,
        created_at=recipient.created_at,
        updated_at=recipient.updated_at,
    )


def _audit_event(event: WhatsAppBroadcastAuditEvent) -> BroadcastAuditEventResponse:
    return BroadcastAuditEventResponse(
        id=event.id,
        command_id=event.command_id,
        recipient_id=event.recipient_id,
        message_id=event.message_id,
        event_type=event.event_type,
        reason_code=event.reason_code,
        actor_user_id=event.actor_user_id,
        affected_count=event.affected_count,
        occurred_at=event.occurred_at,
    )


def _encode_cursor(identifier: int) -> str:
    return urlsafe_b64encode(f"v1:{identifier}".encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int | None:
    if cursor is None:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = urlsafe_b64decode(padded.encode()).decode()
        version, separator, raw_id = decoded.partition(":")
        identifier = int(raw_id)
    except (Base64Error, UnicodeDecodeError, ValueError) as error:
        raise InvalidWhatsAppBroadcastError("Invalid Broadcast cursor") from error
    if version != "v1" or separator != ":" or identifier <= 0:
        raise InvalidWhatsAppBroadcastError("Invalid Broadcast cursor")
    return identifier
