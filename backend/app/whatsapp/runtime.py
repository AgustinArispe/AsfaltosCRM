from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.core.config import (
    get_jwt_secret,
    get_whatsapp_document_max_bytes,
    get_whatsapp_document_mime_types,
    get_whatsapp_image_max_bytes,
    get_whatsapp_image_mime_types,
    get_whatsapp_media_storage_name,
    get_whatsapp_media_storage_root,
    get_whatsapp_provider_name,
)
from app.services.whatsapp_query_observability import (
    NullWhatsAppQueryMetrics,
    WhatsAppQueryMetrics,
)
from app.whatsapp.contracts import WhatsAppProvider
from app.whatsapp.cursors import WhatsAppCursorCodec
from app.whatsapp.fake_provider import FakeWhatsAppProvider
from app.whatsapp.media_storage import (
    FakeMediaStorage,
    FilesystemMediaStorage,
    MediaStorage,
)
from app.whatsapp.media_validation import WhatsAppMediaPolicy


@dataclass(frozen=True, slots=True)
class WhatsAppRuntime:
    provider: WhatsAppProvider
    storage: MediaStorage
    media_policy: WhatsAppMediaPolicy
    cursors: WhatsAppCursorCodec
    metrics: WhatsAppQueryMetrics


def build_fake_whatsapp_runtime(
    *,
    provider: FakeWhatsAppProvider | None = None,
    storage: MediaStorage | None = None,
    media_policy: WhatsAppMediaPolicy | None = None,
    metrics: WhatsAppQueryMetrics | None = None,
) -> WhatsAppRuntime:
    selected_metrics = metrics or NullWhatsAppQueryMetrics()
    return WhatsAppRuntime(
        provider=provider or FakeWhatsAppProvider(freeform_window=timedelta(hours=24)),
        storage=storage or FakeMediaStorage(),
        media_policy=media_policy or _configured_media_policy(),
        cursors=WhatsAppCursorCodec(get_jwt_secret(), selected_metrics),
        metrics=selected_metrics,
    )


def build_configured_whatsapp_runtime() -> WhatsAppRuntime:
    get_whatsapp_provider_name()
    storage: MediaStorage
    if get_whatsapp_media_storage_name() == "filesystem":
        storage = FilesystemMediaStorage(get_whatsapp_media_storage_root())
    else:
        storage = FakeMediaStorage()
    return build_fake_whatsapp_runtime(storage=storage)


def _configured_media_policy() -> WhatsAppMediaPolicy:
    return WhatsAppMediaPolicy(
        image_max_bytes=get_whatsapp_image_max_bytes(),
        document_max_bytes=get_whatsapp_document_max_bytes(),
        image_mime_types=get_whatsapp_image_mime_types(),
        document_mime_types=get_whatsapp_document_mime_types(),
    )
