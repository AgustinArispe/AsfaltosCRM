from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import WhatsAppMessageType, WhatsAppStorageStatus
from app.services.errors import InvalidWhatsAppMessageError
from app.services.whatsapp_media_service import WhatsAppMediaService
from app.services.whatsapp_message_service import OutboundAttachmentInput
from app.whatsapp import (
    MediaPutRequest,
    MediaStorageError,
    StoredMedia,
    StoredMediaContent,
)
from app.whatsapp.media_validation import ValidatedMedia
from app.whatsapp.runtime import WhatsAppRuntime


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

    def upload(self, upload: MediaUploadInput) -> StoredMedia:
        validated = self._validate(
            media_type=upload.media_type,
            content=upload.content,
            mime_type=upload.mime_type,
            filename=upload.filename,
        )
        try:
            return self._runtime.storage.put(
                MediaPutRequest(
                    media_ref=uuid4(),
                    content=validated.content,
                    media_type=validated.media_type,
                    mime_type=validated.mime_type,
                    filename=validated.filename,
                )
            )
        except MediaStorageError as error:
            raise InvalidWhatsAppMessageError("Media storage failed") from error

    def outbound_attachment(
        self,
        media_ref: UUID,
        *,
        expected_type: WhatsAppMessageType,
    ) -> OutboundAttachmentInput:
        stored = self._metadata(media_ref)
        if stored.media_type is not expected_type:
            raise InvalidWhatsAppMessageError(
                "Uploaded media does not match the outbound message type"
            )
        return OutboundAttachmentInput(
            provider_media_id=None,
            storage_key=stored.storage_key,
            mime_type=stored.mime_type,
            filename=stored.filename,
            size_bytes=stored.size_bytes,
        )

    def read_uploaded(self, media_ref: UUID) -> MediaContentResult:
        metadata = self._metadata(media_ref)
        content = self._read_storage(metadata.storage_key)
        validated = self._validate_content(content)
        return MediaContentResult(
            content=validated.content,
            mime_type=validated.mime_type,
            filename=validated.filename,
        )

    def read_attachment(self, attachment_id: int) -> MediaContentResult:
        media_service = WhatsAppMediaService(
            self._session,
            self._runtime.provider,
            self._runtime.storage,
            self._runtime.media_policy,
        )
        result = media_service.download(attachment_id)
        if (
            result.storage_status is not WhatsAppStorageStatus.AVAILABLE
            or result.storage_key is None
        ):
            raise InvalidWhatsAppMessageError("Attachment content is unavailable")
        try:
            content = self._runtime.storage.get(result.storage_key)
            validated = self._runtime.media_policy.validate(
                media_type=content.metadata.media_type,
                content=content.content,
                declared_mime_type=content.metadata.mime_type,
                filename=content.metadata.filename,
            )
        except MediaStorageError as error:
            media_service.mark_storage_failed(
                attachment_id,
                "Stored media content is unavailable",
                expected_storage_key=result.storage_key,
            )
            raise InvalidWhatsAppMessageError(
                "Stored media content is unavailable"
            ) from error
        return MediaContentResult(
            content=validated.content,
            mime_type=validated.mime_type,
            filename=validated.filename,
        )

    def _metadata(self, media_ref: UUID) -> StoredMedia:
        try:
            return self._runtime.storage.get_metadata(media_ref)
        except MediaStorageError as error:
            raise InvalidWhatsAppMessageError(
                "Uploaded media reference is invalid"
            ) from error

    def _read_storage(self, storage_key: str) -> StoredMediaContent:
        try:
            return self._runtime.storage.get(storage_key)
        except MediaStorageError as error:
            raise InvalidWhatsAppMessageError(
                "Stored media content is unavailable"
            ) from error

    def _validate_content(self, content: StoredMediaContent) -> ValidatedMedia:
        return self._validate(
            media_type=content.metadata.media_type,
            content=content.content,
            mime_type=content.metadata.mime_type,
            filename=content.metadata.filename,
        )

    def _validate(
        self,
        *,
        media_type: WhatsAppMessageType,
        content: bytes,
        mime_type: str,
        filename: str | None,
    ) -> ValidatedMedia:
        try:
            return self._runtime.media_policy.validate(
                media_type=media_type,
                content=content,
                declared_mime_type=mime_type,
                filename=filename,
            )
        except MediaStorageError as error:
            raise InvalidWhatsAppMessageError(str(error)) from error
