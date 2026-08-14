from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models import WhatsAppMessageType
from app.services.errors import InvalidWhatsAppMessageError
from app.services.whatsapp_api_media_service import WhatsAppApiMediaService
from app.services.whatsapp_message_service import OutboundAttachmentInput
from app.whatsapp import (
    ProviderTemplateSnapshot,
    TemplateHeaderType,
    TemplateParameter,
    WhatsAppProvider,
)


@dataclass(frozen=True, slots=True)
class HumanTemplateParameterInput:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class HumanTemplateSelection:
    name: str
    language: str
    category: str
    parameter_names: tuple[str, ...]
    header_type: TemplateHeaderType
    header_media_required: bool


@dataclass(frozen=True, slots=True)
class HumanTemplateSendPreparation:
    selection: HumanTemplateSelection
    parameters: tuple[TemplateParameter, ...]
    attachment: OutboundAttachmentInput | None


class WhatsAppHumanTemplateService:
    def __init__(
        self,
        provider: WhatsAppProvider,
        media: WhatsAppApiMediaService,
    ) -> None:
        self._provider = provider
        self._media = media

    def list_usable(self) -> tuple[HumanTemplateSelection, ...]:
        return tuple(
            self._selection(template)
            for template in self._provider.list_templates()
            if self._is_usable(template)
        )

    def prepare_send(
        self,
        *,
        template_name: str,
        language: str,
        parameters: tuple[HumanTemplateParameterInput, ...],
        header_media_ref: UUID | None,
    ) -> HumanTemplateSendPreparation:
        selection = self._find_usable(template_name, language)
        normalized_parameters = self._normalize_parameters(parameters)
        if (
            tuple(item.name for item in normalized_parameters)
            != selection.parameter_names
        ):
            raise InvalidWhatsAppMessageError(
                "Template parameters do not match the selected template"
            )
        attachment = self._header_attachment(selection, header_media_ref)
        return HumanTemplateSendPreparation(
            selection=selection,
            parameters=tuple(
                TemplateParameter(name=item.name, value=item.value)
                for item in normalized_parameters
            ),
            attachment=attachment,
        )

    def _find_usable(
        self,
        template_name: str,
        language: str,
    ) -> HumanTemplateSelection:
        normalized_name = self._required_text(template_name, "Template name")
        normalized_language = self._required_text(language, "Template language")
        template = next(
            (
                item
                for item in self._provider.list_templates()
                if item.name == normalized_name
                and item.language == normalized_language
                and self._is_usable(item)
            ),
            None,
        )
        if template is None:
            raise InvalidWhatsAppMessageError(
                "Selected approved template is not currently available"
            )
        return self._selection(template)

    def _header_attachment(
        self,
        selection: HumanTemplateSelection,
        media_ref: UUID | None,
    ) -> OutboundAttachmentInput | None:
        expected_type = self._media_type(selection.header_type)
        if media_ref is None:
            if selection.header_media_required:
                raise InvalidWhatsAppMessageError(
                    "Selected template requires header media"
                )
            return None
        if expected_type is None:
            raise InvalidWhatsAppMessageError(
                "Selected template does not accept header media"
            )
        attachment = self._media.outbound_attachment(
            media_ref,
            expected_type=expected_type,
        )
        return OutboundAttachmentInput(
            provider_media_id=attachment.provider_media_id,
            storage_key=attachment.storage_key,
            mime_type=attachment.mime_type,
            filename=attachment.filename,
            size_bytes=attachment.size_bytes,
            media_type=expected_type,
        )

    @staticmethod
    def _is_usable(template: ProviderTemplateSnapshot) -> bool:
        return (
            template.category.upper() != "MARKETING"
            and template.status.upper() == "APPROVED"
            and template.supported_for_send
            and (
                not template.header_media_required
                or template.header_type
                in {TemplateHeaderType.IMAGE, TemplateHeaderType.DOCUMENT}
            )
        )

    @classmethod
    def _selection(cls, template: ProviderTemplateSnapshot) -> HumanTemplateSelection:
        parameter_names = tuple(
            cls._required_text(name, "Template parameter name")
            for name in template.parameter_names
        )
        if len(parameter_names) != len(set(parameter_names)):
            raise InvalidWhatsAppMessageError("Template parameter names must be unique")
        return HumanTemplateSelection(
            name=cls._required_text(template.name, "Template name"),
            language=cls._required_text(template.language, "Template language"),
            category=cls._required_text(template.category, "Template category"),
            parameter_names=parameter_names,
            header_type=template.header_type,
            header_media_required=template.header_media_required,
        )

    @classmethod
    def _normalize_parameters(
        cls,
        parameters: tuple[HumanTemplateParameterInput, ...],
    ) -> tuple[HumanTemplateParameterInput, ...]:
        normalized = tuple(
            HumanTemplateParameterInput(
                name=cls._required_text(item.name, "Template parameter name"),
                value=cls._required_text(item.value, "Template parameter value"),
            )
            for item in parameters
        )
        names = tuple(item.name for item in normalized)
        if len(names) != len(set(names)):
            raise InvalidWhatsAppMessageError("Template parameter names must be unique")
        return normalized

    @staticmethod
    def _media_type(header_type: TemplateHeaderType) -> WhatsAppMessageType | None:
        if header_type is TemplateHeaderType.IMAGE:
            return WhatsAppMessageType.IMAGE
        if header_type is TemplateHeaderType.DOCUMENT:
            return WhatsAppMessageType.DOCUMENT
        return None

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise InvalidWhatsAppMessageError(f"{field_name} is required")
        return normalized
