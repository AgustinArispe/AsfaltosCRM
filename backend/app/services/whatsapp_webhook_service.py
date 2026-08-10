from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.whatsapp_inbound_service import (
    InboundAttachmentInput,
    InboundMessageInput,
    WhatsAppInboundService,
)
from app.services.whatsapp_status_service import (
    ProviderStatusInput,
    WhatsAppStatusService,
)
from app.whatsapp.contracts import WhatsAppProvider
from app.whatsapp.webhook_contracts import (
    ProviderIgnoredEvent,
    ProviderInboundEvent,
    ProviderStatusEvent,
    ProviderWebhookEvent,
)


class WhatsAppWebhookService:
    def __init__(self, session: Session, provider: WhatsAppProvider) -> None:
        self._session = session
        self._provider = provider

    def process(self, events: tuple[ProviderWebhookEvent, ...]) -> None:
        for event in events:
            if isinstance(event, ProviderInboundEvent):
                WhatsAppInboundService(self._session, self._provider).receive(
                    InboundMessageInput(
                        external_message_id=event.external_message_id,
                        external_phone=event.external_phone,
                        provider_contact_id=event.provider_contact_id,
                        display_name=event.display_name,
                        message_type=event.message_type,
                        body=event.body,
                        provider_message_at=event.provider_message_at,
                        attachment=(
                            InboundAttachmentInput(
                                provider_media_id=(event.attachment.provider_media_id),
                                mime_type=event.attachment.mime_type,
                                filename=event.attachment.filename,
                                size_bytes=event.attachment.size_bytes,
                            )
                            if event.attachment is not None
                            else None
                        ),
                    )
                )
            elif isinstance(event, ProviderStatusEvent):
                WhatsAppStatusService(self._session).record(
                    ProviderStatusInput(
                        external_message_id=event.external_message_id,
                        state=event.state,
                        occurred_at=event.occurred_at,
                        error_code=event.error_code,
                        error_message=event.error_message,
                    )
                )
            elif isinstance(event, ProviderIgnoredEvent):
                continue
