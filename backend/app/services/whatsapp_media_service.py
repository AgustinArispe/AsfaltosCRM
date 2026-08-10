from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WhatsAppAttachment, WhatsAppStorageStatus
from app.services.errors import EntityNotFoundError, InvalidWhatsAppMessageError
from app.services.whatsapp_projection_service import later_datetime
from app.whatsapp import (
    MediaStorage,
    MediaStorageError,
    ProviderMediaReference,
    StoreMediaRequest,
    WhatsAppProvider,
    WhatsAppProviderError,
)


@dataclass(frozen=True, slots=True)
class StoredAttachmentResult:
    attachment_id: int
    storage_status: WhatsAppStorageStatus
    storage_key: str | None


class WhatsAppMediaService:
    def __init__(
        self,
        session: Session,
        provider: WhatsAppProvider,
        storage: MediaStorage,
    ) -> None:
        self._session = session
        self._provider = provider
        self._storage = storage

    def download(
        self,
        attachment_id: int,
        *,
        now: datetime | None = None,
    ) -> StoredAttachmentResult:
        requested_at = self._aware_utc(now or datetime.now(UTC))
        with self._session.begin():
            attachment = self._session.scalar(
                select(WhatsAppAttachment)
                .where(WhatsAppAttachment.id == attachment_id)
                .with_for_update()
            )
            if attachment is None:
                raise EntityNotFoundError("WhatsAppAttachment", attachment_id)
            if attachment.storage_status is WhatsAppStorageStatus.AVAILABLE:
                return self._result(attachment)
            if attachment.provider_media_id is None:
                raise InvalidWhatsAppMessageError(
                    "Attachment has no provider media ID to download"
                )
            reference = ProviderMediaReference(
                provider_media_id=attachment.provider_media_id,
                storage_key=None,
                mime_type=attachment.mime_type,
                filename=attachment.filename,
            )

        try:
            payload = self._provider.download_media(reference)
            stored = self._storage.store(
                StoreMediaRequest(
                    content=payload.content,
                    mime_type=payload.mime_type,
                    filename=payload.filename,
                )
            )
        except WhatsAppProviderError as error:
            return self._mark_failed(
                attachment_id,
                error.details.safe_message,
                failed_at=requested_at,
            )
        except MediaStorageError as error:
            return self._mark_failed(
                attachment_id,
                str(error),
                failed_at=requested_at,
            )

        with self._session.begin():
            attachment = self._attachment_for_update(attachment_id)
            attachment.storage_key = stored.storage_key
            attachment.storage_status = WhatsAppStorageStatus.AVAILABLE
            attachment.storage_error = None
            attachment.mime_type = stored.mime_type
            attachment.filename = stored.filename
            attachment.size_bytes = stored.size_bytes
            attachment.updated_at = later_datetime(
                attachment.updated_at,
                requested_at,
            )
            self._session.flush()
            return self._result(attachment)

    def _mark_failed(
        self,
        attachment_id: int,
        safe_message: str,
        *,
        failed_at: datetime,
    ) -> StoredAttachmentResult:
        with self._session.begin():
            attachment = self._attachment_for_update(attachment_id)
            attachment.storage_status = WhatsAppStorageStatus.FAILED
            attachment.storage_error = safe_message.strip() or "Media storage failed"
            attachment.updated_at = later_datetime(
                attachment.updated_at,
                failed_at,
            )
            self._session.flush()
            return self._result(attachment)

    def _attachment_for_update(self, attachment_id: int) -> WhatsAppAttachment:
        attachment = self._session.scalar(
            select(WhatsAppAttachment)
            .where(WhatsAppAttachment.id == attachment_id)
            .with_for_update()
        )
        if attachment is None:
            raise EntityNotFoundError("WhatsAppAttachment", attachment_id)
        return attachment

    @staticmethod
    def _result(attachment: WhatsAppAttachment) -> StoredAttachmentResult:
        return StoredAttachmentResult(
            attachment_id=attachment.id,
            storage_status=attachment.storage_status,
            storage_key=attachment.storage_key,
        )

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
