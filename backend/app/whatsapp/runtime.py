from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from threading import Lock
from uuid import UUID, uuid4

from app.core.config import (
    get_jwt_secret,
    get_whatsapp_document_mime_types,
    get_whatsapp_image_mime_types,
    get_whatsapp_media_max_bytes,
    get_whatsapp_provider_name,
)
from app.models import WhatsAppMessageType
from app.services.errors import InvalidWhatsAppMessageError
from app.services.whatsapp_query_observability import (
    NullWhatsAppQueryMetrics,
    WhatsAppQueryMetrics,
)
from app.whatsapp.contracts import WhatsAppProvider
from app.whatsapp.cursors import WhatsAppCursorCodec
from app.whatsapp.fake_provider import FakeWhatsAppProvider
from app.whatsapp.media_storage import FakeMediaStorage, MediaStorage, StoredMedia


@dataclass(frozen=True, slots=True)
class WhatsAppMediaPolicy:
    max_bytes: int
    image_mime_types: frozenset[str]
    document_mime_types: frozenset[str]

    def supports(
        self,
        media_type: WhatsAppMessageType,
        mime_type: str,
    ) -> bool:
        normalized = mime_type.strip().lower()
        if media_type is WhatsAppMessageType.IMAGE:
            return normalized in self.image_mime_types
        if media_type is WhatsAppMessageType.DOCUMENT:
            return normalized in self.document_mime_types
        return False


@dataclass(frozen=True, slots=True)
class UploadedMedia:
    media_ref: UUID
    media_type: WhatsAppMessageType
    stored: StoredMedia


class UploadedMediaRegistry:
    def __init__(self) -> None:
        self._items: dict[UUID, UploadedMedia] = {}
        self._lock = Lock()

    def register(
        self,
        media_type: WhatsAppMessageType,
        stored: StoredMedia,
    ) -> UploadedMedia:
        uploaded = UploadedMedia(
            media_ref=uuid4(),
            media_type=media_type,
            stored=stored,
        )
        with self._lock:
            self._items[uploaded.media_ref] = uploaded
        return uploaded

    def get(self, media_ref: UUID) -> UploadedMedia:
        with self._lock:
            uploaded = self._items.get(media_ref)
        if uploaded is None:
            raise InvalidWhatsAppMessageError("Uploaded media reference is invalid")
        return uploaded


@dataclass(frozen=True, slots=True)
class WhatsAppRuntime:
    provider: WhatsAppProvider
    storage: MediaStorage
    uploads: UploadedMediaRegistry
    media_policy: WhatsAppMediaPolicy
    cursors: WhatsAppCursorCodec
    metrics: WhatsAppQueryMetrics


def build_fake_whatsapp_runtime(
    *,
    provider: FakeWhatsAppProvider | None = None,
    storage: MediaStorage | None = None,
    metrics: WhatsAppQueryMetrics | None = None,
) -> WhatsAppRuntime:
    selected_metrics = metrics or NullWhatsAppQueryMetrics()
    return WhatsAppRuntime(
        provider=provider or FakeWhatsAppProvider(freeform_window=timedelta(hours=24)),
        storage=storage or FakeMediaStorage(),
        uploads=UploadedMediaRegistry(),
        media_policy=WhatsAppMediaPolicy(
            max_bytes=get_whatsapp_media_max_bytes(),
            image_mime_types=get_whatsapp_image_mime_types(),
            document_mime_types=get_whatsapp_document_mime_types(),
        ),
        cursors=WhatsAppCursorCodec(get_jwt_secret(), selected_metrics),
        metrics=selected_metrics,
    )


def build_configured_whatsapp_runtime() -> WhatsAppRuntime:
    get_whatsapp_provider_name()
    return build_fake_whatsapp_runtime()
