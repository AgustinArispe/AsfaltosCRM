from __future__ import annotations

from base64 import b64decode
from binascii import Error as Base64Error
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from re import compile as compile_pattern
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, ValidationError

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
    TemplateHeaderType,
    WhatsAppProviderError,
    WindowDecision,
    WindowEvaluationContext,
)
from app.whatsapp.media_storage import MediaStorage, MediaStorageError
from app.whatsapp.meta_config import MetaConfig
from app.whatsapp.meta_http import (
    MetaGraphClient,
    MetaGraphFailure,
    MetaGraphFailureKind,
)
from app.whatsapp.meta_observability import MetaMetrics, MetaOperation

_CUSTOMER_SERVICE_WINDOW = timedelta(hours=24)
_MAX_TEMPLATE_SNAPSHOT_ITEMS = 500
_TEMPLATE_FIELDS = "id,name,language,category,status,parameter_format,components"
_NAMED_TEMPLATE_PARAMETER = compile_pattern(r"\{\{([a-zA-Z0-9_]+)\}\}")


class _MetaSendMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    message_status: str | None = None


class _MetaSendResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: tuple[_MetaSendMessage, ...]


class _MetaMediaUploadResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str


class _MetaMediaResolutionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    mime_type: str
    sha256: str | None = None
    file_size: int | None = None


class _MetaTemplateComponent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    format: str | None = None
    text: str | None = None


class _MetaTemplateRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    language: str
    category: str
    status: str
    parameter_format: str | None = None
    components: tuple[_MetaTemplateComponent, ...] = ()


class _MetaPagingCursors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    after: str | None = None


class _MetaPaging(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cursors: _MetaPagingCursors | None = None
    next: str | None = None


class _MetaTemplatePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: tuple[_MetaTemplateRecord, ...]
    paging: _MetaPaging | None = None


class _MetaTextContent(BaseModel):
    preview_url: bool = False
    body: str


class _MetaMediaContent(BaseModel):
    id: str
    caption: str | None = None
    filename: str | None = None


class _MetaTemplateLanguage(BaseModel):
    code: str


class _MetaTemplateTextParameter(BaseModel):
    type: str = "text"
    parameter_name: str
    text: str


class _MetaTemplateComponentRequest(BaseModel):
    type: str = "body"
    parameters: tuple[_MetaTemplateTextParameter, ...]


class _MetaTemplateContent(BaseModel):
    name: str
    language: _MetaTemplateLanguage
    components: tuple[_MetaTemplateComponentRequest, ...] = ()


class _MetaTextMessageRequest(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "text"
    text: _MetaTextContent


class _MetaImageMessageRequest(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "image"
    image: _MetaMediaContent


class _MetaDocumentMessageRequest(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "document"
    document: _MetaMediaContent


class _MetaTemplateMessageRequest(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "template"
    template: _MetaTemplateContent


@dataclass(frozen=True, slots=True)
class _TemplateDefinition:
    snapshot: ProviderTemplateSnapshot
    supported_for_send: bool
    parameter_names: frozenset[str]


class MetaTemplateSnapshotCache:
    def __init__(self) -> None:
        self._definitions: tuple[_TemplateDefinition, ...] = ()

    @property
    def snapshots(self) -> tuple[ProviderTemplateSnapshot, ...]:
        return tuple(item.snapshot for item in self._definitions)

    def replace(self, definitions: tuple[_TemplateDefinition, ...]) -> None:
        self._definitions = definitions

    def find(self, name: str, language: str) -> _TemplateDefinition | None:
        return next(
            (
                item
                for item in self._definitions
                if item.snapshot.name == name and item.snapshot.language == language
            ),
            None,
        )


class MetaCloudApiProvider:
    def __init__(
        self,
        config: MetaConfig,
        graph: MetaGraphClient,
        storage: MediaStorage,
        metrics: MetaMetrics,
        *,
        image_max_bytes: int,
        document_max_bytes: int,
        now: Callable[[], datetime] | None = None,
        template_cache: MetaTemplateSnapshotCache | None = None,
    ) -> None:
        self._config = config
        self._graph = graph
        self._storage = storage
        self._metrics = metrics
        self._image_max_bytes = image_max_bytes
        self._document_max_bytes = document_max_bytes
        self._now = now or (lambda: datetime.now(UTC))
        self._templates = template_cache or MetaTemplateSnapshotCache()

    def send_text(self, request: SendTextRequest) -> ProviderSendResult:
        payload = _MetaTextMessageRequest(
            to=_normalized_recipient(request.recipient.phone),
            text=_MetaTextContent(body=_required_text(request.text, "message text")),
        )
        return self._send(payload.model_dump_json().encode(), MetaOperation.SEND_TEXT)

    def send_image(self, request: SendImageRequest) -> ProviderSendResult:
        media_id = self._resolve_outbound_media_id(
            request.media,
            operation=MetaOperation.MEDIA_UPLOAD,
        )
        payload = _MetaImageMessageRequest(
            to=_normalized_recipient(request.recipient.phone),
            image=_MetaMediaContent(
                id=media_id,
                caption=_optional_text(request.caption),
            ),
        )
        return self._send(
            payload.model_dump_json(exclude_none=True).encode(),
            MetaOperation.SEND_IMAGE,
        )

    def send_document(self, request: SendDocumentRequest) -> ProviderSendResult:
        media_id = self._resolve_outbound_media_id(
            request.media,
            operation=MetaOperation.MEDIA_UPLOAD,
        )
        payload = _MetaDocumentMessageRequest(
            to=_normalized_recipient(request.recipient.phone),
            document=_MetaMediaContent(
                id=media_id,
                caption=_optional_text(request.caption),
                filename=_optional_text(request.media.filename),
            ),
        )
        return self._send(
            payload.model_dump_json(exclude_none=True).encode(),
            MetaOperation.SEND_DOCUMENT,
        )

    def send_template(self, request: SendTemplateRequest) -> ProviderSendResult:
        template_name = _required_text(request.template_name, "template name")
        language = _required_text(request.language, "template language")
        definition = self._templates.find(template_name, language)
        if (
            definition is None
            or definition.snapshot.status.upper() != "APPROVED"
            or not definition.supported_for_send
        ):
            raise _provider_error(
                ProviderErrorKind.PERMANENT_FAILURE,
                "META_TEMPLATE_UNSUPPORTED",
                "Meta template is unavailable or unsupported",
            )
        names = tuple(parameter.name.strip() for parameter in request.parameters)
        if (
            any(not name for name in names)
            or len(set(names)) != len(names)
            or frozenset(names) != definition.parameter_names
        ):
            raise _provider_error(
                ProviderErrorKind.PERMANENT_FAILURE,
                "META_TEMPLATE_PARAMETERS_INVALID",
                "Meta template parameters are invalid",
            )
        parameters = tuple(
            _MetaTemplateTextParameter(
                parameter_name=parameter.name.strip(),
                text=parameter.value,
            )
            for parameter in request.parameters
        )
        components = (
            (_MetaTemplateComponentRequest(parameters=parameters),)
            if parameters
            else ()
        )
        payload = _MetaTemplateMessageRequest(
            to=_normalized_recipient(request.recipient.phone),
            template=_MetaTemplateContent(
                name=template_name,
                language=_MetaTemplateLanguage(code=language),
                components=components,
            ),
        )
        return self._send(
            payload.model_dump_json(exclude_none=True).encode(),
            MetaOperation.SEND_TEMPLATE,
        )

    def download_media(
        self,
        reference: ProviderMediaReference,
    ) -> ProviderMediaPayload:
        media_id = _required_text(reference.provider_media_id, "provider media ID")
        maximum = (
            self._image_max_bytes
            if reference.mime_type is not None
            and reference.mime_type.startswith("image/")
            else self._document_max_bytes
        )
        for resolution_attempt in range(2):
            resolved = self._resolve_media(media_id)
            if resolved.file_size is not None and resolved.file_size > maximum:
                raise _provider_error(
                    ProviderErrorKind.PERMANENT_FAILURE,
                    "META_MEDIA_TOO_LARGE",
                    "Meta media exceeds the configured size limit",
                )
            try:
                response = self._graph.download(
                    url=resolved.url,
                    maximum_bytes=maximum,
                )
            except MetaGraphFailure as error:
                if resolution_attempt == 0 and error.code in {
                    "HTTP_401",
                    "HTTP_403",
                    "HTTP_404",
                }:
                    continue
                raise _mapped_graph_error(error) from error
            content_type = _header_value(response.headers, "content-type")
            response_mime = (
                content_type.partition(";")[0].strip().lower()
                if content_type is not None
                else resolved.mime_type.strip().lower()
            )
            if response_mime != resolved.mime_type.strip().lower():
                raise _provider_error(
                    ProviderErrorKind.PERMANENT_FAILURE,
                    "META_MEDIA_MIME_MISMATCH",
                    "Meta media type is inconsistent",
                )
            if (
                resolved.file_size is not None
                and len(response.body) != resolved.file_size
            ):
                raise _provider_error(
                    ProviderErrorKind.PERMANENT_FAILURE,
                    "META_MEDIA_LENGTH_MISMATCH",
                    "Meta media length is inconsistent",
                )
            _verify_provider_checksum(response.body, resolved.sha256)
            return ProviderMediaPayload(
                content=response.body,
                mime_type=response_mime,
                filename=reference.filename,
            )
        raise RuntimeError("Meta media resolution completed without a result")

    def list_templates(self) -> tuple[ProviderTemplateSnapshot, ...]:
        try:
            definitions = self._fetch_all_templates()
        except (MetaGraphFailure, ValidationError, ValueError) as error:
            self._metrics.increment_template_sync("failed")
            if isinstance(error, MetaGraphFailure):
                raise _mapped_graph_error(error) from error
            self._metrics.increment_mapping_failure("template")
            raise _provider_error(
                ProviderErrorKind.RETRYABLE_FAILURE,
                "META_TEMPLATE_SYNC_INVALID",
                "Meta template synchronization failed",
                retryable=True,
            ) from error
        self._templates.replace(definitions)
        self._metrics.increment_template_sync("success")
        return self._templates.snapshots

    def evaluate_window(
        self,
        context: WindowEvaluationContext,
    ) -> WindowDecision:
        now = _aware_utc(context.now)
        if context.last_inbound_at is None:
            return WindowDecision(False, None)
        expires_at = _aware_utc(context.last_inbound_at) + _CUSTOMER_SERVICE_WINDOW
        return WindowDecision(now < expires_at, expires_at)

    def _send(self, body: bytes, operation: MetaOperation) -> ProviderSendResult:
        try:
            response_body = self._graph.request_json(
                operation=operation,
                method="POST",
                path=f"/{self._config.phone_number_id}/messages",
                body=body,
                message_acceptance_possible=True,
            )
        except MetaGraphFailure as error:
            raise _mapped_graph_error(error) from error
        try:
            response = _MetaSendResponse.model_validate_json(response_body)
            external_id = response.messages[0].id.strip()
        except (ValidationError, IndexError) as error:
            self._metrics.increment_mapping_failure("send_response")
            raise _provider_error(
                ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
                "META_ACCEPTANCE_UNKNOWN",
                "Meta message acceptance is unknown",
                retryable=False,
                acceptance_unknown=True,
            ) from error
        if not external_id:
            raise _provider_error(
                ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
                "META_ACCEPTANCE_UNKNOWN",
                "Meta message acceptance is unknown",
                retryable=False,
                acceptance_unknown=True,
            )
        return ProviderSendResult(
            external_message_id=external_id,
            accepted_at=_aware_utc(self._now()),
            initial_state=None,
        )

    def _resolve_outbound_media_id(
        self,
        reference: ProviderMediaReference,
        *,
        operation: MetaOperation,
    ) -> str:
        if reference.provider_media_id is not None:
            return _required_text(reference.provider_media_id, "provider media ID")
        storage_key = _required_text(reference.storage_key, "storage key")
        try:
            stored = self._storage.get(storage_key)
        except MediaStorageError as error:
            raise _provider_error(
                ProviderErrorKind.PERMANENT_FAILURE,
                "META_MEDIA_STORAGE_UNAVAILABLE",
                "Stored media is unavailable",
            ) from error
        boundary = f"----AsfaltosCRM{sha256(stored.content).hexdigest()[:24]}"
        multipart = _multipart_media(
            boundary,
            stored.content,
            stored.metadata.mime_type,
        )
        try:
            response_body = self._graph.request_json(
                operation=operation,
                method="POST",
                path=f"/{self._config.phone_number_id}/media",
                body=multipart,
                content_type=f"multipart/form-data; boundary={boundary}",
            )
            response = _MetaMediaUploadResponse.model_validate_json(response_body)
        except MetaGraphFailure as error:
            raise _mapped_graph_error(error) from error
        except ValidationError as error:
            self._metrics.increment_mapping_failure("media_upload")
            raise _provider_error(
                ProviderErrorKind.RETRYABLE_FAILURE,
                "META_MEDIA_UPLOAD_INVALID",
                "Meta media upload returned an invalid response",
                retryable=True,
            ) from error
        return _required_text(response.id, "uploaded provider media ID")

    def _resolve_media(self, media_id: str) -> _MetaMediaResolutionResponse:
        query = urlencode({"phone_number_id": self._config.phone_number_id})
        try:
            response = self._graph.request_json(
                operation=MetaOperation.MEDIA_RESOLVE,
                method="GET",
                path=f"/{media_id}?{query}",
            )
            resolved = _MetaMediaResolutionResponse.model_validate_json(response)
        except MetaGraphFailure as error:
            raise _mapped_graph_error(error) from error
        except ValidationError as error:
            self._metrics.increment_mapping_failure("media_resolution")
            raise _provider_error(
                ProviderErrorKind.RETRYABLE_FAILURE,
                "META_MEDIA_RESOLUTION_INVALID",
                "Meta media resolution returned an invalid response",
                retryable=True,
            ) from error
        if resolved.id.strip() != media_id:
            raise _provider_error(
                ProviderErrorKind.PERMANENT_FAILURE,
                "META_MEDIA_ID_MISMATCH",
                "Meta media identity is inconsistent",
            )
        return resolved

    def _fetch_all_templates(self) -> tuple[_TemplateDefinition, ...]:
        definitions: list[_TemplateDefinition] = []
        seen_ids: set[str] = set()
        seen_keys: set[tuple[str, str]] = set()
        seen_cursors: set[str] = set()
        after: str | None = None
        while True:
            query_values = {"fields": _TEMPLATE_FIELDS, "limit": "100"}
            if after is not None:
                query_values["after"] = after
            response_body = self._graph.request_json(
                operation=MetaOperation.TEMPLATE_LIST,
                method="GET",
                path=(
                    f"/{self._config.waba_id}/message_templates?"
                    f"{urlencode(query_values)}"
                ),
            )
            page = _MetaTemplatePage.model_validate_json(response_body)
            for record in page.data:
                definition = _template_definition(record)
                key = (definition.snapshot.name, definition.snapshot.language)
                if definition.snapshot.external_id in seen_ids or key in seen_keys:
                    raise ValueError("Meta template snapshot contains duplicates")
                seen_ids.add(definition.snapshot.external_id)
                seen_keys.add(key)
                definitions.append(definition)
                if len(definitions) > _MAX_TEMPLATE_SNAPSHOT_ITEMS:
                    raise ValueError("Meta template snapshot exceeded its limit")
            next_cursor = (
                page.paging.cursors.after
                if page.paging is not None and page.paging.cursors is not None
                else None
            )
            if page.paging is None or page.paging.next is None:
                break
            if next_cursor is None or next_cursor in seen_cursors:
                raise ValueError("Meta template pagination is invalid")
            seen_cursors.add(next_cursor)
            after = next_cursor
        return tuple(definitions)


def _template_definition(record: _MetaTemplateRecord) -> _TemplateDefinition:
    header_components = tuple(
        component
        for component in record.components
        if component.type.upper() == "HEADER"
    )
    if not header_components:
        header_type = TemplateHeaderType.NONE
    else:
        raw_format = (header_components[0].format or "TEXT").upper()
        try:
            header_type = TemplateHeaderType(raw_format)
        except ValueError as error:
            raise ValueError("Unsupported Meta template header type") from error
    component_types = {component.type.upper() for component in record.components}
    supported_components = component_types.issubset({"HEADER", "BODY", "FOOTER"})
    non_body_has_parameters = any(
        component.type.upper() != "BODY"
        and component.text is not None
        and "{{" in component.text
        for component in record.components
    )
    body_parameter_names = frozenset(
        parameter_name
        for component in record.components
        if component.type.upper() == "BODY" and component.text is not None
        for parameter_name in _NAMED_TEMPLATE_PARAMETER.findall(component.text)
    )
    supported_header = (
        len(header_components) <= 1
        and header_type in {TemplateHeaderType.NONE, TemplateHeaderType.TEXT}
        and not non_body_has_parameters
    )
    supported_parameters = (record.parameter_format or "").upper() == "NAMED"
    return _TemplateDefinition(
        snapshot=ProviderTemplateSnapshot(
            external_id=_required_text(record.id, "template ID"),
            name=_required_text(record.name, "template name"),
            language=_required_text(record.language, "template language"),
            category=_required_text(record.category, "template category"),
            status=_required_text(record.status, "template status"),
            header_type=header_type,
        ),
        supported_for_send=(
            supported_components and supported_header and supported_parameters
        ),
        parameter_names=body_parameter_names,
    )


def _multipart_media(boundary: str, content: bytes, mime_type: str) -> bytes:
    if "\r" in mime_type or "\n" in mime_type:
        raise _provider_error(
            ProviderErrorKind.PERMANENT_FAILURE,
            "META_MEDIA_MIME_INVALID",
            "Stored media type is invalid",
        )
    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="messaging_product"\r\n\r\n'
        f"whatsapp\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="type"\r\n\r\n'
        f"{mime_type}\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="upload.bin"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode()
    return prefix + content + f"\r\n--{boundary}--\r\n".encode()


def _verify_provider_checksum(content: bytes, expected: str | None) -> None:
    if expected is None:
        return
    try:
        expected_digest = b64decode(expected, validate=True)
    except (Base64Error, ValueError) as error:
        raise _provider_error(
            ProviderErrorKind.PERMANENT_FAILURE,
            "META_MEDIA_CHECKSUM_INVALID",
            "Meta media checksum is invalid",
        ) from error
    if not compare_digest(sha256(content).digest(), expected_digest):
        raise _provider_error(
            ProviderErrorKind.PERMANENT_FAILURE,
            "META_MEDIA_CHECKSUM_MISMATCH",
            "Meta media integrity verification failed",
        )


def _mapped_graph_error(error: MetaGraphFailure) -> WhatsAppProviderError:
    mapping = {
        MetaGraphFailureKind.PERMANENT: ProviderErrorKind.PERMANENT_FAILURE,
        MetaGraphFailureKind.RETRYABLE: ProviderErrorKind.RETRYABLE_FAILURE,
        MetaGraphFailureKind.TIMEOUT_BEFORE: (
            ProviderErrorKind.TIMEOUT_BEFORE_ACCEPTANCE
        ),
        MetaGraphFailureKind.ACCEPTANCE_UNKNOWN: (
            ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE
        ),
    }
    kind = mapping[error.kind]
    return _provider_error(
        kind,
        error.code,
        error.safe_message,
        retryable=error.kind
        in {MetaGraphFailureKind.RETRYABLE, MetaGraphFailureKind.TIMEOUT_BEFORE},
        acceptance_unknown=error.kind is MetaGraphFailureKind.ACCEPTANCE_UNKNOWN,
    )


def _provider_error(
    kind: ProviderErrorKind,
    code: str | None,
    safe_message: str,
    *,
    retryable: bool = False,
    acceptance_unknown: bool = False,
) -> WhatsAppProviderError:
    return WhatsAppProviderError(
        ProviderErrorDetails(
            kind=kind,
            code=code,
            safe_message=safe_message,
            retryable=retryable,
            acceptance_unknown=acceptance_unknown,
        )
    )


def _required_text(value: str | None, label: str) -> str:
    normalized = value.strip() if value is not None else ""
    if not normalized:
        raise _provider_error(
            ProviderErrorKind.PERMANENT_FAILURE,
            "META_REQUEST_INVALID",
            f"Meta {label} is required",
        )
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalized_recipient(phone: str) -> str:
    normalized = "".join(character for character in phone if character.isdecimal())
    if not normalized:
        raise _provider_error(
            ProviderErrorKind.PERMANENT_FAILURE,
            "META_RECIPIENT_INVALID",
            "Meta recipient is invalid",
        )
    return normalized


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware")
    return value.astimezone(UTC)


def _header_value(
    headers: tuple[tuple[str, str], ...],
    name: str,
) -> str | None:
    lowered = name.lower()
    return next((value for key, value in headers if key.lower() == lowered), None)
