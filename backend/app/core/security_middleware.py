from __future__ import annotations

from json import dumps

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import RequestBodyLimits

_BODY_TOO_LARGE_DETAIL = "Request body too large"
_CSP = (
    "default-src 'none'; base-uri 'self'; object-src 'none'; "
    "frame-ancestors 'none'; form-action 'self'; script-src 'self'; "
    "style-src 'self'; connect-src 'self'; font-src 'self'; "
    "img-src 'self' blob:; media-src 'self' blob:"
)


class RequestBodyTooLargeError(Exception):
    """Raised before an oversized protected request reaches application parsing."""


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, limits: RequestBodyLimits) -> None:
        self._app = app
        self._limits = limits

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        maximum = _body_limit(scope, self._limits)
        if maximum is None:
            await self._app(scope, receive, send)
            return
        if _declared_content_length_exceeds(scope, maximum):
            await _send_body_too_large(send)
            return

        received_bytes = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > maximum:
                    raise RequestBodyTooLargeError
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self._app(scope, limited_receive, tracked_send)
        except RequestBodyTooLargeError:
            if not response_started:
                await _send_body_too_large(send)


class ProductionSecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}
                for name, value in _security_headers():
                    if name not in existing:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        await self._app(scope, receive, secure_send)


def _body_limit(scope: Scope, limits: RequestBodyLimits) -> int | None:
    if scope["type"] != "http" or scope["method"] != "POST":
        return None
    path = scope["path"]
    if path == "/api/intake/web":
        return limits.web_intake_bytes
    if path == "/api/whatsapp/provider/webhook":
        return limits.meta_webhook_bytes
    if path == "/api/whatsapp/media":
        return limits.whatsapp_media_bytes
    if path == "/api/customer-imports/dry-run":
        return limits.customer_import_bytes
    return None


def _declared_content_length_exceeds(scope: Scope, maximum: int) -> bool:
    for name, value in scope.get("headers", []):
        if name.lower() != b"content-length":
            continue
        try:
            return int(value) > maximum
        except ValueError:
            return False
    return False


async def _send_body_too_large(send: Send) -> None:
    body = dumps({"detail": _BODY_TOO_LARGE_DETAIL}, separators=(",", ":")).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _security_headers() -> tuple[tuple[bytes, bytes], ...]:
    return (
        (b"content-security-policy", _CSP.encode()),
        (b"strict-transport-security", b"max-age=31536000"),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (
            b"permissions-policy",
            b"camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        ),
    )
