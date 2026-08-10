from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, Response, status
from fastapi.responses import PlainTextResponse

from app.api.dependencies import DatabaseSession
from app.services.whatsapp_webhook_service import WhatsAppWebhookService
from app.whatsapp.runtime import WhatsAppRuntime
from app.whatsapp.webhook_contracts import ProviderWebhookMappingError


def create_whatsapp_provider_webhook_router(
    runtime: WhatsAppRuntime,
) -> APIRouter:
    if runtime.webhook is None:
        raise ValueError("Provider webhook runtime is required")
    webhook = runtime.webhook
    router = APIRouter(prefix="/whatsapp/provider/webhook", tags=["whatsapp-provider"])

    @router.get("")
    def verify_subscription(
        mode: Annotated[str | None, Query(alias="hub.mode")] = None,
        verify_token: Annotated[
            str | None,
            Query(alias="hub.verify_token"),
        ] = None,
        challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
    ) -> PlainTextResponse:
        verified = webhook.verify_challenge(
            mode=mode,
            verify_token=verify_token,
            challenge=challenge,
        )
        if verified is None:
            return PlainTextResponse(
                "Webhook verification failed",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return PlainTextResponse(verified)

    @router.post("")
    async def receive_events(
        request: Request,
        session: DatabaseSession,
        signature: Annotated[
            str | None,
            Header(alias="X-Hub-Signature-256"),
        ] = None,
    ) -> Response:
        raw_body = await request.body()
        if not webhook.verify_signature(raw_body, signature):
            return Response(status_code=status.HTTP_403_FORBIDDEN)
        try:
            events = webhook.map_events(raw_body)
        except ProviderWebhookMappingError:
            return Response(status_code=status.HTTP_400_BAD_REQUEST)
        WhatsAppWebhookService(session, runtime.provider).process(events)
        return Response(status_code=status.HTTP_200_OK)

    return router
