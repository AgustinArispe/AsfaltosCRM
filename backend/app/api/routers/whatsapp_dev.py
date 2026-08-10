from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.whatsapp_presenter import WhatsAppApiPresenter
from app.models import WhatsAppProviderState
from app.schemas.whatsapp import (
    FakeInboundMediaRequest,
    FakeInboundRequest,
    FakeInboundResponse,
    FakeProviderBehaviorRequest,
    FakeProviderBehaviorResponse,
    FakeStatusResultResponse,
    FakeStatusSequenceRequest,
    FakeStatusSequenceResponse,
)
from app.services import (
    InboundAttachmentInput,
    InboundMessageInput,
    MessageQueryService,
    ProviderStatusInput,
    WhatsAppInboundService,
    WhatsAppStatusService,
)
from app.services.errors import InvalidWhatsAppMessageError
from app.services.whatsapp_api_media_service import WhatsAppApiMediaService
from app.whatsapp import FakeWhatsAppProvider, MediaStorageError, ProviderMediaPayload
from app.whatsapp.runtime import WhatsAppRuntime


def create_whatsapp_dev_router(
    runtime: WhatsAppRuntime,
    provider: FakeWhatsAppProvider,
) -> APIRouter:
    router = APIRouter(prefix="/whatsapp/dev", tags=["whatsapp-dev"])
    presenter = WhatsAppApiPresenter(provider)

    @router.post("/inbound", response_model=FakeInboundResponse)
    def inject_inbound(
        payload: FakeInboundRequest,
        response: Response,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> FakeInboundResponse:
        result = WhatsAppInboundService(session, provider).receive(
            _inbound_input(payload, session, runtime, provider),
            now=datetime.now(UTC),
        )
        projection = MessageQueryService(session, runtime.metrics).get_message(
            result.message_id
        )
        response.status_code = (
            status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        )
        return FakeInboundResponse(
            created=result.created,
            message=presenter.message(projection),
        )

    @router.post(
        "/messages/{message_id}/statuses",
        response_model=FakeStatusSequenceResponse,
    )
    def simulate_statuses(
        message_id: int,
        payload: FakeStatusSequenceRequest,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> FakeStatusSequenceResponse:
        message = MessageQueryService(session, runtime.metrics).get_message(message_id)
        if message.external_message_id is None:
            raise InvalidWhatsAppMessageError(
                "Message has no external ID for provider status simulation"
            )
        session.commit()
        results: list[FakeStatusResultResponse] = []
        for requested_event in payload.events:
            state = WhatsAppProviderState(requested_event.state.value)
            events = provider.emit_delivery_events(
                message.external_message_id,
                (state,),
                duplicate=payload.duplicate,
                occurred_at=requested_event.occurred_at,
                error_code=requested_event.error_code,
                error_message=requested_event.error_message,
            )
            for event in events:
                result = WhatsAppStatusService(session).record(
                    ProviderStatusInput(
                        external_message_id=event.external_message_id,
                        state=event.state,
                        occurred_at=event.occurred_at,
                        error_code=event.error_code,
                        error_message=event.error_message,
                    )
                )
                results.append(
                    FakeStatusResultResponse(
                        event_id=result.event_id,
                        message_id=result.message_id,
                        created=result.created,
                    )
                )
        updated = MessageQueryService(session, runtime.metrics).get_message(message_id)
        return FakeStatusSequenceResponse(
            results=results,
            message=presenter.message(updated),
        )

    @router.put(
        "/provider-behaviors/{client_generated_id}",
        response_model=FakeProviderBehaviorResponse,
    )
    def configure_provider_behavior(
        client_generated_id: UUID,
        payload: FakeProviderBehaviorRequest,
        _current_user: CurrentUser,
    ) -> FakeProviderBehaviorResponse:
        provider.configure_error(
            client_generated_id,
            payload.kind,
            code=payload.code,
            safe_message=payload.safe_message,
        )
        return FakeProviderBehaviorResponse(
            client_generated_id=client_generated_id,
            kind=payload.kind,
        )

    return router


def _inbound_input(
    payload: FakeInboundRequest,
    session: DatabaseSession,
    runtime: WhatsAppRuntime,
    provider: FakeWhatsAppProvider,
) -> InboundMessageInput:
    if isinstance(payload, FakeInboundMediaRequest):
        try:
            stored = runtime.storage.get_metadata(payload.media_ref)
        except MediaStorageError as error:
            raise InvalidWhatsAppMessageError(
                "Uploaded media reference is invalid"
            ) from error
        if stored.media_type is not payload.message_type:
            raise InvalidWhatsAppMessageError(
                "Uploaded media does not match the inbound message type"
            )
        content = WhatsAppApiMediaService(session, runtime).read_uploaded(
            payload.media_ref
        )
        provider_media_id = f"fake-upload-{payload.media_ref}"
        provider.add_media(
            provider_media_id,
            ProviderMediaPayload(
                content=content.content,
                mime_type=content.mime_type,
                filename=content.filename,
            ),
        )
        attachment = InboundAttachmentInput(
            provider_media_id=provider_media_id,
            mime_type=content.mime_type,
            filename=content.filename,
            size_bytes=len(content.content),
        )
        body = payload.caption
    else:
        attachment = None
        body = payload.body
    return InboundMessageInput(
        external_message_id=payload.external_message_id,
        external_phone=payload.external_phone,
        provider_contact_id=payload.provider_contact_id,
        display_name=payload.display_name,
        message_type=payload.message_type,
        body=body,
        provider_message_at=payload.provider_message_at,
        attachment=attachment,
    )
