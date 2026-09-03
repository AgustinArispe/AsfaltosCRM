from __future__ import annotations

from app.whatsapp.contracts import (
    ProviderErrorDetails,
    ProviderErrorKind,
    ProviderMediaPayload,
    ProviderMediaReference,
    ProviderSendResult,
    ProviderTemplateSnapshot,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    WhatsAppProviderError,
    WindowDecision,
    WindowEvaluationContext,
)


class DisabledWhatsAppProvider:
    """Explicit no-network provider used while WhatsApp is disabled."""

    def send_text(self, request: SendTextRequest) -> ProviderSendResult:
        del request
        raise _disabled_error()

    def send_image(self, request: SendImageRequest) -> ProviderSendResult:
        del request
        raise _disabled_error()

    def send_document(self, request: SendDocumentRequest) -> ProviderSendResult:
        del request
        raise _disabled_error()

    def send_template(self, request: SendTemplateRequest) -> ProviderSendResult:
        del request
        raise _disabled_error()

    def download_media(
        self,
        reference: ProviderMediaReference,
    ) -> ProviderMediaPayload:
        del reference
        raise _disabled_error()

    def list_templates(self) -> tuple[ProviderTemplateSnapshot, ...]:
        return ()

    def evaluate_window(
        self,
        context: WindowEvaluationContext,
    ) -> WindowDecision:
        del context
        return WindowDecision(can_send_freeform=False, window_expires_at=None)


def _disabled_error() -> WhatsAppProviderError:
    return WhatsAppProviderError(
        ProviderErrorDetails(
            kind=ProviderErrorKind.PERMANENT_FAILURE,
            code="WHATSAPP_DISABLED",
            safe_message="WhatsApp provider is disabled",
            retryable=False,
            acceptance_unknown=False,
        )
    )
