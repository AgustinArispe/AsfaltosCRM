from argparse import ArgumentParser
from uuid import uuid4

from app.core.config import get_runtime_security_settings
from app.db.session import SessionLocal
from app.services.whatsapp_broadcast_service import WhatsAppBroadcastService
from app.whatsapp import DisabledWhatsAppProvider
from app.whatsapp.runtime import build_configured_whatsapp_runtime


def parse_broadcast_id() -> int:
    parser = ArgumentParser(description="Process one bounded WhatsApp Broadcast batch")
    parser.add_argument("broadcast_id", type=int)
    value = parser.parse_args().broadcast_id
    if not isinstance(value, int):
        raise SystemExit("broadcast_id must be an integer")
    return value


def main() -> None:
    broadcast_id = parse_broadcast_id()
    if broadcast_id <= 0:
        raise SystemExit("broadcast_id must be positive")
    get_runtime_security_settings()
    runtime = build_configured_whatsapp_runtime()
    if isinstance(runtime.provider, DisabledWhatsAppProvider):
        raise SystemExit("WhatsApp provider is disabled")
    with SessionLocal() as session:
        result = WhatsAppBroadcastService(
            session,
            runtime.provider,
            runtime.storage,
            batch_size=runtime.broadcast_batch_size,
            claim_timeout=runtime.broadcast_claim_timeout,
        ).process_batch(
            broadcast_id,
            command_id=uuid4(),
            actor_user_id=None,
        )
    print(
        f"broadcast={result.broadcast_id} claimed={result.claimed_count} "
        f"completed={result.completed_count} remaining={result.remaining_count}"
    )


if __name__ == "__main__":
    main()
