from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.core.config import (
    get_jwt_secret,
    get_whatsapp_broadcast_batch_size,
    get_whatsapp_broadcast_claim_timeout_seconds,
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
from app.whatsapp.meta_config import MetaConfig
from app.whatsapp.meta_http import HttpsMetaHttpTransport, MetaGraphClient
from app.whatsapp.meta_observability import NullMetaMetrics
from app.whatsapp.meta_provider import MetaCloudApiProvider
from app.whatsapp.meta_webhook import (
    MetaWebhookIntegration,
    MetaWebhookMapper,
    MetaWebhookVerifier,
)
from app.whatsapp.webhook_contracts import ProviderWebhook


@dataclass(frozen=True, slots=True)
class WhatsAppRuntime:
    provider: WhatsAppProvider
    storage: MediaStorage
    media_policy: WhatsAppMediaPolicy
    cursors: WhatsAppCursorCodec
    metrics: WhatsAppQueryMetrics
    broadcast_batch_size: int
    broadcast_claim_timeout: timedelta
    webhook: ProviderWebhook | None = None


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
        broadcast_batch_size=get_whatsapp_broadcast_batch_size(),
        broadcast_claim_timeout=timedelta(
            seconds=get_whatsapp_broadcast_claim_timeout_seconds()
        ),
        webhook=None,
    )


def build_configured_whatsapp_runtime() -> WhatsAppRuntime:
    provider_name = get_whatsapp_provider_name()
    storage: MediaStorage
    if get_whatsapp_media_storage_name() == "filesystem":
        storage = FilesystemMediaStorage(get_whatsapp_media_storage_root())
    else:
        storage = FakeMediaStorage()
    if provider_name == "fake":
        return build_fake_whatsapp_runtime(storage=storage)
    return build_meta_whatsapp_runtime(storage=storage)


def build_meta_whatsapp_runtime(
    *,
    config: MetaConfig | None = None,
    storage: MediaStorage | None = None,
) -> WhatsAppRuntime:
    selected_config = config or MetaConfig.from_environment()
    selected_storage = storage or FakeMediaStorage()
    meta_metrics = NullMetaMetrics()
    graph = MetaGraphClient(
        selected_config,
        HttpsMetaHttpTransport(),
        meta_metrics,
    )
    provider = MetaCloudApiProvider(
        selected_config,
        graph,
        selected_storage,
        meta_metrics,
        image_max_bytes=get_whatsapp_image_max_bytes(),
        document_max_bytes=get_whatsapp_document_max_bytes(),
    )
    webhook = MetaWebhookIntegration(
        MetaWebhookVerifier(
            verify_token=selected_config.webhook_verify_token,
            app_secret=selected_config.app_secret,
        ),
        MetaWebhookMapper(
            waba_id=selected_config.waba_id,
            phone_number_id=selected_config.phone_number_id,
            metrics=meta_metrics,
        ),
    )
    query_metrics = NullWhatsAppQueryMetrics()
    return WhatsAppRuntime(
        provider=provider,
        storage=selected_storage,
        media_policy=_configured_media_policy(),
        cursors=WhatsAppCursorCodec(get_jwt_secret(), query_metrics),
        metrics=query_metrics,
        broadcast_batch_size=get_whatsapp_broadcast_batch_size(),
        broadcast_claim_timeout=timedelta(
            seconds=get_whatsapp_broadcast_claim_timeout_seconds()
        ),
        webhook=webhook,
    )


def _configured_media_policy() -> WhatsAppMediaPolicy:
    return WhatsAppMediaPolicy(
        image_max_bytes=get_whatsapp_image_max_bytes(),
        document_max_bytes=get_whatsapp_document_max_bytes(),
        image_mime_types=get_whatsapp_image_mime_types(),
        document_mime_types=get_whatsapp_document_mime_types(),
    )
