from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WhatsAppAttachment, WhatsAppMessageType, WhatsAppStorageStatus
from app.services.errors import InvalidWhatsAppMessageError
from app.services.whatsapp_media_service import WhatsAppMediaService
from app.services.whatsapp_message_service import OutboundAttachmentInput
from app.whatsapp import (
    MediaStorageError,
    StoredMediaContent,
    StoreMediaRequest,
)
from app.whatsapp.runtime import UploadedMedia, WhatsAppRuntime


@dataclass(frozen=True, slots=True)
class MediaUploadInput:
    media_type: WhatsAppMessageType
    content: bytes
    mime_type: str
    filename: str | None


@dataclass(frozen=True, slots=True)
class MediaContentResult:
    content: bytes
    mime_type: str
    filename: str | None


class WhatsAppApiMediaService:
    def __init__(
        self,
        session: Session,
        runtime: WhatsAppRuntime,
    ) -> None:
        self._session = session
        self._runtime = runtime

    def upload(self, upload: MediaUploadInput) -> UploadedMedia:
        mime_type = upload.mime_type.strip().lower()
        filename = _sanitized_filename(upload.filename)
        if not upload.content:
            raise InvalidWhatsAppMessageError("Uploaded media cannot be empty")
        if len(upload.content) > self._runtime.media_policy.max_bytes:
            raise InvalidWhatsAppMessageError("Uploaded media exceeds the size limit")
        if not self._runtime.media_policy.supports(upload.media_type, mime_type):
            raise InvalidWhatsAppMessageError(
                "Uploaded media type or MIME type is not allowed"
            )
        try:
            stored = self._runtime.storage.store(
                StoreMediaRequest(
                    content=upload.content,
                    mime_type=mime_type,
                    filename=filename,
                )
            )
        except MediaStorageError as error:
            raise InvalidWhatsAppMessageError("Media storage failed") from error
        return self._runtime.uploads.register(upload.media_type, stored)

    def outbound_attachment(
        self,
        media_ref: UUID,
        *,
        expected_type: WhatsAppMessageType,
    ) -> OutboundAttachmentInput:
        uploaded = self._runtime.uploads.get(media_ref)
        if uploaded.media_type is not expected_type:
            raise InvalidWhatsAppMessageError(
                "Uploaded media does not match the outbound message type"
            )
        return OutboundAttachmentInput(
            provider_media_id=None,
            storage_key=uploaded.stored.storage_key,
            mime_type=uploaded.stored.mime_type,
            filename=uploaded.stored.filename,
            size_bytes=uploaded.stored.size_bytes,
        )

    def read_uploaded(self, media_ref: UUID) -> MediaContentResult:
        uploaded = self._runtime.uploads.get(media_ref)
        content = self._read_storage(uploaded.stored.storage_key)
        self._validate_stored_content(uploaded.media_type, content)
        return MediaContentResult(
            content=content.content,
            mime_type=content.mime_type,
            filename=_sanitized_filename(content.filename),
        )

    def read_attachment(self, attachment_id: int) -> MediaContentResult:
        result = WhatsAppMediaService(
            self._session,
            self._runtime.provider,
            self._runtime.storage,
        ).download(attachment_id)
        if (
            result.storage_status is not WhatsAppStorageStatus.AVAILABLE
            or result.storage_key is None
        ):
            raise InvalidWhatsAppMessageError("Attachment content is unavailable")
        content = self._read_storage(result.storage_key)
        with self._session.begin():
            media_type = self._session.scalar(
                select(WhatsAppAttachment.media_type).where(
                    WhatsAppAttachment.id == attachment_id
                )
            )
        if media_type is None:
            raise InvalidWhatsAppMessageError("Attachment metadata is unavailable")
        self._validate_stored_content(media_type, content)
        return MediaContentResult(
            content=content.content,
            mime_type=content.mime_type,
            filename=_sanitized_filename(content.filename),
        )

    def _read_storage(self, storage_key: str) -> StoredMediaContent:
        try:
            return self._runtime.storage.read(storage_key)
        except (FileNotFoundError, MediaStorageError) as error:
            raise InvalidWhatsAppMessageError(
                "Stored media content is unavailable"
            ) from error

    def _validate_stored_content(
        self,
        media_type: WhatsAppMessageType,
        content: StoredMediaContent,
    ) -> None:
        if len(content.content) > self._runtime.media_policy.max_bytes:
            raise InvalidWhatsAppMessageError("Stored media exceeds the size limit")
        if not self._runtime.media_policy.supports(media_type, content.mime_type):
            raise InvalidWhatsAppMessageError("Stored media MIME type is not allowed")


def _sanitized_filename(filename: str | None) -> str | None:
    if filename is None:
        return None
    leaf = PurePath(filename.replace("\\", "/")).name
    cleaned = "".join(
        character for character in leaf if character.isprintable()
    ).strip()
    return cleaned or None
