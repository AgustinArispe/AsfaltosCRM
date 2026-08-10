from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from app.models import WhatsAppMessageType
from app.whatsapp.media_storage import MediaStorageError


@dataclass(frozen=True, slots=True)
class ValidatedMedia:
    content: bytes
    media_type: WhatsAppMessageType
    mime_type: str
    filename: str | None


@dataclass(frozen=True, slots=True)
class WhatsAppMediaPolicy:
    image_max_bytes: int
    document_max_bytes: int
    image_mime_types: frozenset[str]
    document_mime_types: frozenset[str]

    def __post_init__(self) -> None:
        if self.image_max_bytes <= 0 or self.document_max_bytes <= 0:
            raise ValueError("WhatsApp media limits must be greater than zero")
        if not self.image_mime_types or not self.document_mime_types:
            raise ValueError("WhatsApp media MIME allowlists cannot be empty")

    def max_bytes_for(self, media_type: WhatsAppMessageType) -> int:
        if media_type is WhatsAppMessageType.IMAGE:
            return self.image_max_bytes
        if media_type is WhatsAppMessageType.DOCUMENT:
            return self.document_max_bytes
        raise MediaStorageError("WhatsApp media type is not supported")

    def validate(
        self,
        *,
        media_type: WhatsAppMessageType,
        content: bytes,
        declared_mime_type: str,
        filename: str | None,
    ) -> ValidatedMedia:
        if not content:
            raise MediaStorageError("Media content cannot be empty")
        if len(content) > self.max_bytes_for(media_type):
            raise MediaStorageError("Media content exceeds the configured size limit")
        declared = declared_mime_type.strip().lower()
        allowed = (
            self.image_mime_types
            if media_type is WhatsAppMessageType.IMAGE
            else self.document_mime_types
        )
        if declared not in allowed:
            raise MediaStorageError("Media MIME type is not allowed")
        detected = _detected_media(content)
        if detected is None:
            raise MediaStorageError("Media content type could not be verified")
        detected_type, detected_mime = detected
        if detected_type is not media_type or detected_mime != declared:
            raise MediaStorageError("Declared and detected media types do not match")
        return ValidatedMedia(
            content=content,
            media_type=media_type,
            mime_type=detected_mime,
            filename=sanitize_media_filename(filename),
        )


def sanitize_media_filename(filename: str | None) -> str | None:
    if filename is None:
        return None
    leaf = PurePath(filename.replace("\\", "/")).name
    cleaned = "".join(
        character for character in leaf if character.isprintable()
    ).strip()
    return cleaned or None


def _detected_media(
    content: bytes,
) -> tuple[WhatsAppMessageType, str] | None:
    if content.startswith(b"\xff\xd8\xff"):
        return WhatsAppMessageType.IMAGE, "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return WhatsAppMessageType.IMAGE, "image/png"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return WhatsAppMessageType.IMAGE, "image/webp"
    if content.startswith(b"%PDF-"):
        return WhatsAppMessageType.DOCUMENT, "application/pdf"
    return None
