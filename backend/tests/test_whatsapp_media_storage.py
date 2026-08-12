from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import (
    get_whatsapp_broadcast_batch_size,
    get_whatsapp_document_max_bytes,
    get_whatsapp_image_max_bytes,
    get_whatsapp_media_storage_name,
    get_whatsapp_media_storage_root,
)
from app.models import WhatsAppMessageType
from app.whatsapp import (
    FilesystemMediaStorage,
    MediaPutRequest,
    MediaStorageConflictError,
    MediaStorageError,
    MediaStorageIntegrityError,
    MediaStorageNotFoundError,
    WhatsAppMediaPolicy,
)
from app.whatsapp.media_validation import sanitize_media_filename
from app.whatsapp.runtime import build_configured_whatsapp_runtime

IMAGE_REF = UUID("40000000-0000-0000-0000-000000000001")
DOCUMENT_REF = UUID("40000000-0000-0000-0000-000000000002")
PNG_CONTENT = b"\x89PNG\r\n\x1a\nvalidated-png"
PDF_CONTENT = b"%PDF-1.7 validated-pdf"


def test_broadcast_batch_configuration_defaults_to_ten_and_rejects_larger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WHATSAPP_BROADCAST_BATCH_SIZE", raising=False)
    get_whatsapp_broadcast_batch_size.cache_clear()
    assert get_whatsapp_broadcast_batch_size() == 10

    monkeypatch.setenv("WHATSAPP_BROADCAST_BATCH_SIZE", "11")
    get_whatsapp_broadcast_batch_size.cache_clear()
    with pytest.raises(RuntimeError, match="no greater than 10"):
        get_whatsapp_broadcast_batch_size()
    get_whatsapp_broadcast_batch_size.cache_clear()


def media_policy(
    *, image_limit: int = 1024, document_limit: int = 1024
) -> WhatsAppMediaPolicy:
    return WhatsAppMediaPolicy(
        image_max_bytes=image_limit,
        document_max_bytes=document_limit,
        image_mime_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
        document_mime_types=frozenset({"application/pdf"}),
    )


@pytest.mark.parametrize(
    ("media_ref", "media_type", "mime_type", "filename", "content"),
    [
        (IMAGE_REF, WhatsAppMessageType.IMAGE, "image/png", "obra.png", PNG_CONTENT),
        (
            DOCUMENT_REF,
            WhatsAppMessageType.DOCUMENT,
            "application/pdf",
            "ficha.pdf",
            PDF_CONTENT,
        ),
    ],
)
def test_filesystem_storage_round_trip_survives_adapter_restart(
    tmp_path: Path,
    media_ref: UUID,
    media_type: WhatsAppMessageType,
    mime_type: str,
    filename: str,
    content: bytes,
) -> None:
    validated = media_policy().validate(
        media_type=media_type,
        content=content,
        declared_mime_type=mime_type,
        filename=filename,
    )
    request = MediaPutRequest(
        media_ref=media_ref,
        content=validated.content,
        media_type=validated.media_type,
        mime_type=validated.mime_type,
        filename=validated.filename,
    )
    first_adapter = FilesystemMediaStorage(tmp_path)
    stored = first_adapter.put(request)

    restarted_adapter = FilesystemMediaStorage(tmp_path)
    restored = restarted_adapter.get_metadata(media_ref)
    content_result = restarted_adapter.get(restored.storage_key)

    assert restored == stored
    assert content_result.content == content
    assert content_result.metadata.sha256 == stored.sha256
    assert len(stored.sha256) == 64
    assert filename not in stored.storage_key
    assert not hasattr(first_adapter, "delete")


def test_filesystem_storage_put_is_idempotent_and_conflict_safe(
    tmp_path: Path,
) -> None:
    storage = FilesystemMediaStorage(tmp_path)
    request = MediaPutRequest(
        media_ref=DOCUMENT_REF,
        content=PDF_CONTENT,
        media_type=WhatsAppMessageType.DOCUMENT,
        mime_type="application/pdf",
        filename="ficha.pdf",
    )

    first = storage.put(request)
    second = storage.put(request)

    assert second == first
    with pytest.raises(MediaStorageConflictError):
        storage.put(
            MediaPutRequest(
                media_ref=DOCUMENT_REF,
                content=b"%PDF-1.7 different",
                media_type=WhatsAppMessageType.DOCUMENT,
                mime_type="application/pdf",
                filename="ficha.pdf",
            )
        )
    assert storage.get(first.storage_key).content == PDF_CONTENT


def test_filesystem_storage_rejects_traversal_and_symlink_escape(
    tmp_path: Path,
) -> None:
    storage = FilesystemMediaStorage(tmp_path / "media")
    with pytest.raises(MediaStorageNotFoundError):
        storage.get("../outside")
    with pytest.raises(MediaStorageNotFoundError):
        storage.get("/etc/passwd")

    stored = storage.put(
        MediaPutRequest(
            media_ref=DOCUMENT_REF,
            content=PDF_CONTENT,
            media_type=WhatsAppMessageType.DOCUMENT,
            mime_type="application/pdf",
            filename="ficha.pdf",
        )
    )
    outside = tmp_path / "outside"
    outside.write_bytes(PDF_CONTENT)
    content_path = tmp_path / "media" / "v1" / DOCUMENT_REF.hex / "content"
    content_path.unlink()
    content_path.symlink_to(outside)

    with pytest.raises(MediaStorageIntegrityError):
        storage.get(stored.storage_key)

    symlink_root = tmp_path / "linked-root"
    symlink_root.symlink_to(tmp_path / "media", target_is_directory=True)
    with pytest.raises(MediaStorageError):
        FilesystemMediaStorage(symlink_root)


def test_filesystem_storage_atomic_failure_leaves_no_partial_object(
    tmp_path: Path,
) -> None:
    storage = FailingFilesystemMediaStorage(tmp_path)
    request = MediaPutRequest(
        media_ref=DOCUMENT_REF,
        content=PDF_CONTENT,
        media_type=WhatsAppMessageType.DOCUMENT,
        mime_type="application/pdf",
        filename="ficha.pdf",
    )

    with pytest.raises(MediaStorageError, match="write failed") as captured:
        storage.put(request)

    assert str(tmp_path) not in str(captured.value)
    assert list((tmp_path / "v1").iterdir()) == []
    with pytest.raises(MediaStorageNotFoundError):
        storage.get_metadata(DOCUMENT_REF)


def test_filesystem_storage_detects_checksum_corruption(tmp_path: Path) -> None:
    storage = FilesystemMediaStorage(tmp_path)
    stored = storage.put(
        MediaPutRequest(
            media_ref=DOCUMENT_REF,
            content=PDF_CONTENT,
            media_type=WhatsAppMessageType.DOCUMENT,
            mime_type="application/pdf",
            filename="ficha.pdf",
        )
    )
    content_path = tmp_path / "v1" / DOCUMENT_REF.hex / "content"
    content_path.write_bytes(b"X" * len(PDF_CONTENT))

    with pytest.raises(MediaStorageIntegrityError, match="checksum"):
        storage.get(stored.storage_key)


@pytest.mark.parametrize(
    ("media_type", "mime_type", "content"),
    [
        (WhatsAppMessageType.IMAGE, "image/jpeg", b"\xff\xd8\xffjpeg"),
        (WhatsAppMessageType.IMAGE, "image/png", PNG_CONTENT),
        (WhatsAppMessageType.IMAGE, "image/webp", b"RIFF1234WEBPdata"),
        (WhatsAppMessageType.DOCUMENT, "application/pdf", PDF_CONTENT),
    ],
)
def test_media_policy_accepts_inspected_image_and_pdf_content(
    media_type: WhatsAppMessageType,
    mime_type: str,
    content: bytes,
) -> None:
    validated = media_policy().validate(
        media_type=media_type,
        content=content,
        declared_mime_type=mime_type,
        filename="../unsafe\\safe-file.pdf",
    )

    assert validated.mime_type == mime_type
    assert validated.filename == "safe-file.pdf"


@pytest.mark.parametrize(
    ("media_type", "mime_type", "content", "image_limit", "document_limit"),
    [
        (WhatsAppMessageType.IMAGE, "image/png", b"", 1024, 1024),
        (WhatsAppMessageType.IMAGE, "image/jpeg", PNG_CONTENT, 1024, 1024),
        (WhatsAppMessageType.DOCUMENT, "application/pdf", b"not-pdf", 1024, 1024),
        (WhatsAppMessageType.IMAGE, "image/png", PNG_CONTENT, 3, 1024),
        (WhatsAppMessageType.DOCUMENT, "application/pdf", PDF_CONTENT, 1024, 3),
    ],
)
def test_media_policy_rejects_empty_mismatch_unknown_and_oversized_content(
    media_type: WhatsAppMessageType,
    mime_type: str,
    content: bytes,
    image_limit: int,
    document_limit: int,
) -> None:
    with pytest.raises(MediaStorageError):
        media_policy(
            image_limit=image_limit,
            document_limit=document_limit,
        ).validate(
            media_type=media_type,
            content=content,
            declared_mime_type=mime_type,
            filename="file.bin",
        )


def test_filesystem_storage_rejects_non_media_message_type(tmp_path: Path) -> None:
    storage = FilesystemMediaStorage(tmp_path / "media")

    with pytest.raises(MediaStorageError, match="type is invalid"):
        storage.put(
            MediaPutRequest(
                media_ref=UUID("40000000-0000-0000-0000-000000000003"),
                content=b"text",
                media_type=WhatsAppMessageType.TEXT,
                mime_type="text/plain",
                filename=None,
            )
        )


def test_filename_sanitization_never_preserves_path_or_controls() -> None:
    assert sanitize_media_filename("../../obra\\plano\x00.pdf") == "plano.pdf"
    assert sanitize_media_filename("\x00\n") is None
    assert sanitize_media_filename(None) is None


def test_configured_runtime_selects_persistent_filesystem_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_media_config_caches()
    monkeypatch.setenv("WHATSAPP_MEDIA_STORAGE", "filesystem")
    monkeypatch.setenv("WHATSAPP_MEDIA_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_IMAGE_MAX_BYTES", "123")
    monkeypatch.setenv("WHATSAPP_DOCUMENT_MAX_BYTES", "456")
    try:
        runtime = build_configured_whatsapp_runtime()
        assert isinstance(runtime.storage, FilesystemMediaStorage)
        assert get_whatsapp_media_storage_name() == "filesystem"
        assert get_whatsapp_media_storage_root() == tmp_path
        assert get_whatsapp_image_max_bytes() == 123
        assert get_whatsapp_document_max_bytes() == 456
    finally:
        _clear_media_config_caches()


class FailingFilesystemMediaStorage(FilesystemMediaStorage):
    def _before_promote(self, temporary: Path) -> None:
        del temporary
        raise OSError("Injected atomic write failure")


def _clear_media_config_caches() -> None:
    get_whatsapp_media_storage_name.cache_clear()
    get_whatsapp_media_storage_root.cache_clear()
    get_whatsapp_image_max_bytes.cache_clear()
    get_whatsapp_document_max_bytes.cache_clear()
