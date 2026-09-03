from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn
from uuid import uuid4

import pytest

from app.scripts import process_whatsapp_broadcast
from app.whatsapp import (
    DisabledWhatsAppProvider,
    ProviderRecipient,
    SendTextRequest,
    WhatsAppProviderError,
)


@dataclass(frozen=True, slots=True)
class _DisabledRuntime:
    provider: DisabledWhatsAppProvider


def test_disabled_provider_rejects_outbound_messages_without_network() -> None:
    provider = DisabledWhatsAppProvider()

    with pytest.raises(WhatsAppProviderError, match="WhatsApp provider is disabled"):
        provider.send_text(
            SendTextRequest(
                recipient=ProviderRecipient(phone="+541161000001"),
                client_generated_id=uuid4(),
                text="Mensaje de prueba",
            )
        )


def test_broadcast_processor_stops_before_database_work_when_provider_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_session_local() -> NoReturn:
        raise AssertionError("Disabled provider must not process a broadcast")

    monkeypatch.setattr(process_whatsapp_broadcast, "parse_broadcast_id", lambda: 1)
    monkeypatch.setattr(
        process_whatsapp_broadcast,
        "build_configured_whatsapp_runtime",
        lambda: _DisabledRuntime(DisabledWhatsAppProvider()),
    )
    monkeypatch.setattr(
        process_whatsapp_broadcast,
        "SessionLocal",
        unexpected_session_local,
    )

    with pytest.raises(SystemExit, match="WhatsApp provider is disabled"):
        process_whatsapp_broadcast.main()
