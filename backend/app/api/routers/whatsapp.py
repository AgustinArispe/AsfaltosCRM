from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.whatsapp_presenter import WhatsAppApiPresenter
from app.models import WhatsAppDispatchState, WhatsAppMessageType
from app.schemas.whatsapp import (
    ConversationChangePageResponse,
    ConversationDetailResponse,
    ConversationPageResponse,
    ConversationSummaryResponse,
    DocumentOutboundRequest,
    HumanTemplateResponse,
    HumanTemplateSendRequest,
    ImageOutboundRequest,
    MediaUploadMetadata,
    MediaUploadResponse,
    MessageChangePageResponse,
    MessagePageResponse,
    OpportunityLinkRequest,
    OutboundMessageRequest,
    OutboundMessageResponse,
    TextOutboundRequest,
)
from app.services import (
    ChangePageRequest,
    ConversationListFilters,
    ConversationPageRequest,
    ConversationQueryService,
    HumanTemplateParameterInput,
    MessagePageRequest,
    MessageQueryService,
    OutboundMessageInput,
    PollingQueryService,
    WhatsAppConversationService,
    WhatsAppHumanTemplateService,
    WhatsAppMessageService,
)
from app.services.whatsapp_api_media_service import (
    MediaContentResult,
    MediaUploadInput,
    WhatsAppApiMediaService,
)
from app.services.whatsapp_query_observability import WhatsAppCursorKind
from app.whatsapp.runtime import WhatsAppRuntime


def create_whatsapp_router(runtime: WhatsAppRuntime) -> APIRouter:
    router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
    presenter = WhatsAppApiPresenter(runtime.provider)

    @router.get("/conversations", response_model=ConversationPageResponse)
    def list_conversations(
        session: DatabaseSession,
        _current_user: CurrentUser,
        limit: Annotated[int, Query(ge=1, le=50)] = 50,
        page_cursor: str | None = None,
        waiting_only: bool = False,
        unread_only: bool = False,
        search: Annotated[str | None, Query(max_length=255)] = None,
    ) -> ConversationPageResponse:
        cursor = (
            runtime.cursors.decode_conversation_page(page_cursor)
            if page_cursor is not None
            else None
        )
        result = ConversationQueryService(session, runtime.metrics).list_conversations(
            ConversationListFilters(
                waiting_only=waiting_only,
                unread_only=unread_only,
                search=search,
            ),
            ConversationPageRequest(limit=limit, cursor=cursor),
        )
        now = datetime.now(UTC)
        return ConversationPageResponse(
            items=[
                presenter.conversation_summary(item, now=now) for item in result.items
            ],
            next_page_cursor=(
                runtime.cursors.encode_conversation_page(result.next_cursor)
                if result.next_cursor is not None
                else None
            ),
            sync_cursor=runtime.cursors.encode_resource_change(result.sync_cursor),
        )

    @router.get(
        "/conversations/changes",
        response_model=ConversationChangePageResponse,
    )
    def list_conversation_changes(
        session: DatabaseSession,
        _current_user: CurrentUser,
        cursor: str,
        limit: Annotated[int, Query(ge=1, le=500)] = 500,
    ) -> ConversationChangePageResponse:
        decoded = runtime.cursors.decode_resource_change(
            cursor,
            kind=WhatsAppCursorKind.CONVERSATION_CHANGES,
        )
        result = PollingQueryService(
            session,
            runtime.metrics,
        ).list_conversation_changes(ChangePageRequest(decoded, limit=limit))
        now = datetime.now(UTC)
        return ConversationChangePageResponse(
            items=[
                presenter.conversation_summary(item, now=now) for item in result.items
            ],
            next_cursor=runtime.cursors.encode_resource_change(result.next_cursor),
            has_more=result.has_more,
        )

    @router.get(
        "/conversations/{conversation_id}",
        response_model=ConversationDetailResponse,
    )
    def get_conversation(
        conversation_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> ConversationDetailResponse:
        detail = ConversationQueryService(
            session,
            runtime.metrics,
        ).get_conversation_detail(conversation_id)
        return presenter.conversation_detail(detail, now=datetime.now(UTC))

    @router.get(
        "/conversations/{conversation_id}/templates",
        response_model=list[HumanTemplateResponse],
    )
    def list_human_templates(
        conversation_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> list[HumanTemplateResponse]:
        ConversationQueryService(session, runtime.metrics).get_conversation_detail(
            conversation_id
        )
        templates = WhatsAppHumanTemplateService(
            runtime.provider,
            WhatsAppApiMediaService(session, runtime),
        ).list_usable()
        return [
            HumanTemplateResponse(
                name=item.name,
                language=item.language,
                category=item.category,
                parameter_names=list(item.parameter_names),
                header_type=item.header_type,
                header_media_required=item.header_media_required,
            )
            for item in templates
        ]

    @router.get(
        "/conversations/{conversation_id}/messages",
        response_model=MessagePageResponse,
    )
    def list_messages(
        conversation_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        before_cursor: str | None = None,
    ) -> MessagePageResponse:
        before = (
            runtime.cursors.decode_message_page(before_cursor)
            if before_cursor is not None
            else None
        )
        result = MessageQueryService(session, runtime.metrics).list_message_history(
            conversation_id,
            MessagePageRequest(limit=limit, before=before),
        )
        return MessagePageResponse(
            items=[presenter.message(item) for item in result.items],
            next_before_cursor=(
                runtime.cursors.encode_message_page(result.next_before_cursor)
                if result.next_before_cursor is not None
                else None
            ),
            sync_cursor=runtime.cursors.encode_resource_change(result.sync_cursor),
        )

    @router.get(
        "/conversations/{conversation_id}/messages/changes",
        response_model=MessageChangePageResponse,
    )
    def list_message_changes(
        conversation_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
        cursor: str,
        limit: Annotated[int, Query(ge=1, le=500)] = 500,
    ) -> MessageChangePageResponse:
        ConversationQueryService(session, runtime.metrics).get_conversation_detail(
            conversation_id
        )
        decoded = runtime.cursors.decode_resource_change(
            cursor,
            kind=WhatsAppCursorKind.MESSAGE_CHANGES,
        )
        result = MessageQueryService(session, runtime.metrics).list_message_changes(
            conversation_id,
            ChangePageRequest(decoded, limit=limit),
        )
        return MessageChangePageResponse(
            items=[presenter.message(item) for item in result.items],
            next_cursor=runtime.cursors.encode_resource_change(result.next_cursor),
            has_more=result.has_more,
        )

    @router.post(
        "/conversations/{conversation_id}/messages",
        response_model=OutboundMessageResponse,
    )
    def send_message(
        conversation_id: int,
        payload: OutboundMessageRequest,
        response: Response,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> OutboundMessageResponse:
        requested_at = datetime.now(UTC)
        message_input = _outbound_input(
            payload,
            conversation_id=conversation_id,
            user_id=current_user.id,
            media=WhatsAppApiMediaService(session, runtime),
        )
        result = WhatsAppMessageService(session, runtime.provider).send(
            message_input,
            now=requested_at,
        )
        projection = MessageQueryService(session, runtime.metrics).get_message(
            result.message_id
        )
        conversation = ConversationQueryService(
            session,
            runtime.metrics,
        ).get_conversation_detail(conversation_id)
        response.status_code = _outbound_status(result.created, result.dispatch_state)
        return presenter.outbound_message(
            projection,
            conversation.summary,
            now=requested_at,
        )

    @router.post(
        "/conversations/{conversation_id}/templates/send",
        response_model=OutboundMessageResponse,
    )
    def send_human_template(
        conversation_id: int,
        payload: HumanTemplateSendRequest,
        response: Response,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> OutboundMessageResponse:
        requested_at = datetime.now(UTC)
        media = WhatsAppApiMediaService(session, runtime)
        prepared = WhatsAppHumanTemplateService(
            runtime.provider,
            media,
        ).prepare_send(
            template_name=payload.template_name,
            language=payload.language,
            parameters=tuple(
                HumanTemplateParameterInput(name=item.name, value=item.value)
                for item in payload.parameters
            ),
            header_media_ref=payload.header_media_ref,
        )
        result = WhatsAppMessageService(session, runtime.provider).send(
            OutboundMessageInput(
                conversation_id=conversation_id,
                client_generated_id=payload.client_generated_id,
                sent_by_user_id=current_user.id,
                message_type=WhatsAppMessageType.TEXT,
                body=None,
                attachment=prepared.attachment,
                template_name=prepared.selection.name,
                template_language=prepared.selection.language,
                template_parameters=prepared.parameters,
            ),
            now=requested_at,
        )
        projection = MessageQueryService(session, runtime.metrics).get_message(
            result.message_id
        )
        conversation = ConversationQueryService(
            session,
            runtime.metrics,
        ).get_conversation_detail(conversation_id)
        response.status_code = _outbound_status(result.created, result.dispatch_state)
        return presenter.outbound_message(
            projection,
            conversation.summary,
            now=requested_at,
        )

    @router.post(
        "/conversations/{conversation_id}/read",
        response_model=ConversationSummaryResponse,
    )
    def mark_conversation_read(
        conversation_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> ConversationSummaryResponse:
        WhatsAppConversationService(session).mark_as_read(conversation_id)
        detail = ConversationQueryService(
            session,
            runtime.metrics,
        ).get_conversation_detail(conversation_id)
        return presenter.conversation_summary(detail.summary, now=datetime.now(UTC))

    @router.put(
        "/conversations/{conversation_id}/opportunity-link",
        response_model=ConversationDetailResponse,
    )
    def link_opportunity(
        conversation_id: int,
        payload: OpportunityLinkRequest,
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> ConversationDetailResponse:
        WhatsAppConversationService(session).link_opportunity(
            conversation_id,
            payload.opportunity_id,
            linked_by_user_id=current_user.id,
        )
        return _conversation_detail(
            session,
            runtime,
            presenter,
            conversation_id,
        )

    @router.delete(
        "/conversations/{conversation_id}/opportunity-link",
        response_model=ConversationDetailResponse,
    )
    def unlink_opportunity(
        conversation_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> ConversationDetailResponse:
        WhatsAppConversationService(session).unlink_opportunity(conversation_id)
        return _conversation_detail(
            session,
            runtime,
            presenter,
            conversation_id,
        )

    @router.post(
        "/media",
        response_model=MediaUploadResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_media(
        session: DatabaseSession,
        _current_user: CurrentUser,
        file: Annotated[UploadFile, File()],
        metadata: Annotated[str, Form()],
    ) -> MediaUploadResponse:
        parsed = _media_metadata(metadata)
        content = await file.read(
            runtime.media_policy.max_bytes_for(parsed.media_type) + 1
        )
        uploaded = WhatsAppApiMediaService(session, runtime).upload(
            MediaUploadInput(
                media_type=parsed.media_type,
                content=content,
                mime_type=file.content_type or "",
                filename=file.filename,
            )
        )
        return MediaUploadResponse(
            media_ref=uploaded.media_ref,
            media_type=uploaded.media_type,
            mime_type=uploaded.mime_type,
            filename=uploaded.filename,
            size_bytes=uploaded.size_bytes,
            content_url=f"/api/whatsapp/media/{uploaded.media_ref}/content",
        )

    @router.get("/media/{media_ref}/content")
    def read_uploaded_media(
        media_ref: UUID,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> StreamingResponse:
        content = WhatsAppApiMediaService(session, runtime).read_uploaded(media_ref)
        return _media_response(content)

    @router.get("/attachments/{attachment_id}/content")
    def read_attachment(
        attachment_id: int,
        session: DatabaseSession,
        _current_user: CurrentUser,
    ) -> StreamingResponse:
        content = WhatsAppApiMediaService(session, runtime).read_attachment(
            attachment_id
        )
        return _media_response(content)

    return router


def _outbound_input(
    payload: OutboundMessageRequest,
    *,
    conversation_id: int,
    user_id: int,
    media: WhatsAppApiMediaService,
) -> OutboundMessageInput:
    if isinstance(payload, TextOutboundRequest):
        return OutboundMessageInput(
            conversation_id=conversation_id,
            client_generated_id=payload.client_generated_id,
            sent_by_user_id=user_id,
            message_type=WhatsAppMessageType.TEXT,
            body=payload.body,
            retry_of_message_id=payload.retry_of_message_id,
        )
    if isinstance(payload, ImageOutboundRequest):
        message_type = WhatsAppMessageType.IMAGE
    elif isinstance(payload, DocumentOutboundRequest):
        message_type = WhatsAppMessageType.DOCUMENT
    else:
        raise TypeError("Unsupported outbound request")
    return OutboundMessageInput(
        conversation_id=conversation_id,
        client_generated_id=payload.client_generated_id,
        sent_by_user_id=user_id,
        message_type=message_type,
        body=payload.caption,
        attachment=media.outbound_attachment(
            payload.media_ref,
            expected_type=message_type,
        ),
        retry_of_message_id=payload.retry_of_message_id,
    )


def _outbound_status(created: bool, dispatch_state: WhatsAppDispatchState) -> int:
    if dispatch_state is WhatsAppDispatchState.UNKNOWN:
        return status.HTTP_202_ACCEPTED
    if created and dispatch_state is WhatsAppDispatchState.ACCEPTED:
        return status.HTTP_201_CREATED
    return status.HTTP_200_OK


def _conversation_detail(
    session: DatabaseSession,
    runtime: WhatsAppRuntime,
    presenter: WhatsAppApiPresenter,
    conversation_id: int,
) -> ConversationDetailResponse:
    detail = ConversationQueryService(
        session,
        runtime.metrics,
    ).get_conversation_detail(conversation_id)
    return presenter.conversation_detail(detail, now=datetime.now(UTC))


def _media_metadata(raw_metadata: str) -> MediaUploadMetadata:
    try:
        return MediaUploadMetadata.model_validate_json(raw_metadata)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid media metadata",
        ) from error


def _media_response(content: MediaContentResult) -> StreamingResponse:
    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    disposition = "inline" if content.mime_type.startswith("image/") else "attachment"
    headers["Content-Disposition"] = f"{disposition}; filename*=UTF-8''" + quote(
        _download_filename(content), safe=""
    )
    return StreamingResponse(
        _content_chunks(content.content),
        media_type=content.mime_type,
        headers=headers,
    )


def _content_chunks(content: bytes) -> Iterator[bytes]:
    yield content


def _download_filename(content: MediaContentResult) -> str:
    if content.filename is not None:
        return content.filename
    if content.mime_type == "application/pdf":
        return "attachment.pdf"
    if content.mime_type == "image/jpeg":
        return "attachment.jpg"
    if content.mime_type == "image/png":
        return "attachment.png"
    if content.mime_type == "image/webp":
        return "attachment.webp"
    return "attachment"
